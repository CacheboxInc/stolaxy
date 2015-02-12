#!/usr/bin/python

#
# Copyright 2014 Cachebox, Inc. All rights reserved. This software
# is property of Cachebox, Inc and contains trade secrects,
# confidential & proprietary information. Use, disclosure or copying
# this without explicit written permission from Cachebox, Inc is
# prohibited.
#
# Author: Cachebox, Inc (sales@cachebox.com)
#

import sys, time, threading, os
import google.protobuf.internal.encoder as encoder
import google.protobuf.internal.decoder as decoder
import socket 

import twisted
import struct
from twisted.python import failure
from twisted.internet import reactor, error, address, tcp, task
from twisted.internet.protocol import Protocol, Factory, ClientFactory
from twisted.protocols import basic
from twisted.web import server, resource
from twisted.python import log

sys.path.append("./proto_compiled")
import DatanodeProtocol_pb2 as DatanodeProtocol
import IpcConnectionContext_pb2 as IpcConnectionContext
import RpcPayloadHeader_pb2 as RpcPayloadHeader
import hadoop_rpc_pb2 as hadoop_rpc
import hdfs_pb2 as hdfs
import datatransfer_pb2 as datatransfer

# TBD : readfrom xml 
global data_dir
data_dir=""

thread_counter = 0
threads = []
keep_running = 1
BUFSIZE = 64 * 1024
chunk_size = 512
checksum_per_chunk_size = 4
packet_size = 64 * 1024 
max_chunks_per_packet = 127
user_defined_params = ["namenode_ip", "datanode_ip", "namenode_port", "datanode_xferport", "datanode_infoport", "datanode_ipcport", "datanode_dir" , "StorageID"]

HEX_FILTER=''.join([(len(repr(chr(x)))==3) and chr(x) or '.' for x in range(256)])
def hexdump(prefix, src, length=16):
  N=0; result=''
  while src:
    s,src = src[:length],src[length:]
    hexa = ' '.join(["%02X"%ord(x) for x in s])
    s = s.translate(HEX_FILTER)
    result += "%s %04X   %-*s   %s\n" % (prefix, N, length*3, hexa, s)
    N+=length
  return result

def get_free_capacity(datadir):
	statvfs = os.statvfs(datadir)
	return statvfs.f_frsize * statvfs.f_bavail

class Node():
  def __init__(self, configuration):
    self.ipAddr = configuration['datanode_ip'] 
    self.hostName = configuration['datanode_name']
    self.xferPort = int(configuration['datanode_xferport'])
    self.infoPort = int(configuration['datanode_infoport'])
    self.ipcPort = int(configuration['datanode_ipcport']) 
    self.capacity = int(configuration['datadir_capacity']) 
    self.dfsUsed = 0 
    self.remaining = int(configuration['datadir_capacity'])
    self.blockPoolUsed =  0
    self.version = "2.0.1-alpha"

class DatanodeClientProtocol(Protocol):

  #def __init__(self, storageID, nodeinfo, dataxceiver):
  def __init__(self, storageID, nodeinfo):
    self.storageinfo = None
    self._heartbeat = None
    self.heartbeat_interval = 3 
    self.blockreport_interval = 1800
    self.MAX_LENGTH = 99999
    self.storageID = storageID
    self.nodeinfo = nodeinfo
    #self.dataxceiver = dataxceiver
    self.remaining = ""
    self.callid = 0
    self.callbacks = {}
    self.heartbeat_cnt = 0
    self.keep_running = 1

  def send_heartbeat(self):

	'''
	Send protcol, write a generic one 
	1. Length of the next two parts	uint32
	2. RpcPayloadHeaderProto length	varint
	3. RpcPayloadHeaderProto protobuf serialized message
	4. HadoopRpcRequestProto length	varint
	5. HadoopRpcRequestProto protobuf serialized message
	'''
	
        print "[%d] Heartbeat request."  %(int(self.callid))	
	protocol = "org.apache.hadoop.hdfs.server.protocol.DatanodeProtocol"

	''' Making of 3, the RPC header '''
	header = RpcPayloadHeader.RpcPayloadHeaderProto()
	#header.rpcKind = RpcPayloadHeader.RPC_WRITABLE
	#header.rpcKind = RpcPayloadHeader.RPC_PROTOCOL_BUFFER
	#header.rpcOp = RpcPayloadHeader.RPC_FINAL_PAYLOAD
	header.rpcKind = 2
	header.rpcOp = 0
	header.callId = self.callid

	# Like writeto delimiter in Java
	''' making of 2 '''
	headerout = header.SerializeToString()
	headerout = encoder._VarintBytes(len(headerout)) + headerout

	self.callbacks[self.callid] = self.HeartbeatResponse
	self.callid = self.callid + 1

	''' Making of 5 '''
	rpcreq = hadoop_rpc.HadoopRpcRequestProto()
	rpcreq.methodName = "sendHeartbeat"

	# The data blob in request, need to be filled 
	# later, after creating the blob

	rpcreq.request = ""
	rpcreq.declaringClassProtocolName = protocol
	rpcreq.clientProtocolVersion = 1

	''' Create the blob for registration '''
	proto_data = DatanodeProtocol.HeartbeatRequestProto()
	proto_data.registration.CopyFrom(self.datanode_reponse_info)

	'''
	proto_data.registration.datanodeID.ipAddr = self.nodeinfo.ipAddr
	proto_data.registration.datanodeID.hostName = self.nodeinfo.hostName
	proto_data.registration.datanodeID.storageID = self.storageID
	proto_data.registration.datanodeID.xferPort = self.nodeinfo.xferPort
	proto_data.registration.datanodeID.infoPort = self.nodeinfo.infoPort
	proto_data.registration.datanodeID.ipcPort = self.nodeinfo.ipcPort
	'''
	
	'''	
	proto_data.StorageInfoProto.layoutVersion = 
	proto_data.StorageInfoProt.namespceID = 
	proto_data.StorageInfoProt.clusterID = 
	proto_data.StorageInfoProt.ctime = 
	proto_data.registration.storageInfo.CopyFrom(self.storageinfo)
	proto_data.registration.keys.isBlockTokenEnabled = False
	proto_data.registration.keys.keyUpdateInterval = 1
	proto_data.registration.keys.tokenLifeTime = 10
	
	proto_data.registration.keys.currentKey.keyId = 1
	proto_data.registration.keys.currentKey.expiryDate = 2
	proto_data.registration.keys.currentKey.keyBytes = ""
	'''

	''' allKeys in the protcol buffer is of type repeated, why ?? '''
	#proto_data.registration.keys.allKeys.keyId = 1
	#proto_data.registration.keys.allKeys.expiryDate = 2 
	#proto_data.registration.keys.allKeys.keyBytes = ""
	'''
	proto_data.registration.softwareVersion = self.nodeinfo.version
	'''

	# repeated has an add() function that creates a new message 
	# object, appends it to the list, and returns it for the caller 
	# to fill in.

	report = proto_data.reports.add()
	report.storageID =  self.storageID
	report.failed = False	
	report.capacity = self.nodeinfo.capacity
	report.dfsUsed = self.nodeinfo.dfsUsed
	report.remaining = self.nodeinfo.remaining
	report.blockPoolUsed = self.nodeinfo.blockPoolUsed
	
	proto_data.xmitsInProgress =  0
	proto_data.xceiverCount = 0
	proto_data.failedVolumes = 0

	# Bytes corresponding to blob 
	rpcreq.request = proto_data.SerializeToString()
	
	''' making of 4 '''
	reqout = rpcreq.SerializeToString()
	reqout = encoder._VarintBytes(len(reqout)) + reqout

	''' making of 1 '''
	buf = headerout + reqout
	#print "length : %d" %len(buf)
	
	# number of outstanding heartbeats 
	self.heartbeat_cnt += 1
	while True:
	  try:
		self.transport.write(struct.pack(">I", len(buf)))
		self.transport.write(buf)
		#self.transport.write("\n")
		break
	  except:
		print "Something Failed in cotnext of transport."

  def BlockReportResponseProto(self, message, callid=None):
	print "In BlockReportResponseProto"
	pass

  def send_blockreport(self):

	'''
	Send protcol, write a generic one 
	1. Length of the next two parts	uint32
	2. RpcPayloadHeaderProto length	varint
	3. RpcPayloadHeaderProto protobuf serialized message
	4. HadoopRpcRequestProto length	varint
	5. HadoopRpcRequestProto protobuf serialized message
	'''
	
        print "Block report...."	
	entries = os.listdir(data_dir)
	if not len(entries):
	    print "no block file"
	    return 0

	protocol = "org.apache.hadoop.hdfs.server.protocol.DatanodeProtocol"

	''' Making of 3, the RPC header '''
	header = RpcPayloadHeader.RpcPayloadHeaderProto()
	#header.rpcKind = RpcPayloadHeader.RPC_WRITABLE
	#header.rpcKind = RpcPayloadHeader.RPC_PROTOCOL_BUFFER
	#header.rpcOp = RpcPayloadHeader.RPC_FINAL_PAYLOAD
	header.rpcKind = 2
	header.rpcOp = 0
	header.callId = self.callid

	# Like writeto delimiter in Java
	''' making of 2 '''
	headerout = header.SerializeToString()
	headerout = encoder._VarintBytes(len(headerout)) + headerout

	self.callbacks[self.callid] = self.BlockReportResponseProto
	self.callid = self.callid + 1

	''' Making of 5 '''
	rpcreq = hadoop_rpc.HadoopRpcRequestProto()
	rpcreq.methodName = "sendHeartbeat"

	# The data blob in request, need to be filled 
	# later, after creating the blob

	rpcreq.request = ""
	rpcreq.declaringClassProtocolName = protocol
	rpcreq.clientProtocolVersion = 1

	''' Create the blob for registration '''
	proto_data = DatanodeProtocol.BlockReportRequestProto()
	proto_data.registration.CopyFrom(self.datanode_reponse_info)

	# TBD : Get the Pool ID, that can be done easily if we create separate 
	# directory for each poolID and put all related files there. For now 
	# we are getting it from the name of file, unecessarlay in each 
	# itteration

	poolID = None
	sbreport = proto_data.reports.add()
	for file in entries:
		if file.endswith("meta"):
			continue

		print "Filename for block report..", file
		breakup = file.split("-")
		poolID = (breakup[0]) + "-" + (breakup[1]) + "-" + (breakup[2]) + "-" + (breakup[3])
		blockID = long(breakup[4])
		sbreport.blocks.append(blockID)

	sbreport.storage.storageID = self.storageID
	sbreport.storage.state = 0
	proto_data.blockPoolId = poolID

	# Bytes corresponding to blob 
	rpcreq.request = sbreport.SerializeToString()
	
	''' making of 4 '''
	reqout = rpcreq.SerializeToString()
	reqout = encoder._VarintBytes(len(reqout)) + reqout

	''' making of 1 '''
	buf = headerout + reqout
	self.transport.write(struct.pack(">I", len(buf)))
	self.transport.write(buf)

  def RegisterResponse(self, message, callid=None):
        print "Got the ACK for data node register request."
        ''' Start the heartbeat message, create a thread 
	separately to do so, No one will wait to call 
	join on it '''
	data_protocol = DatanodeProtocol.RegisterDatanodeResponseProto()
	data_protocol.ParseFromString(message)
	self.datanode_reponse_info = data_protocol.registration

	global thread_counter, threads
	self.string = "start-heartbeat"
        t = ThreadClass(thread_counter, self)
        threads.append(t)
        thread_counter += 1
        t.start()

	'''
	# Same variable self.string is getting used here 
	# Wait for hearbeat thread to read that context. 
	# A better way is to flag the case that heartbeat 
	# thread has been started successfully started.
	time.sleep(10)
	#Create a thread to send the block report
	self.string = "start-blockreport"
        t = ThreadClass(thread_counter, self)
        threads.append(t)
        thread_counter += 1
        t.start()
	'''

  def HeartbeatResponse (self, message, callid=None):
        print "[%d] Heartbeat response." %int(callid)
	self.heartbeat_cnt -= 1
       	
  def RegisterDataNode(self):
	
	'''
	Send protcol, write a generic one 
	1. Length of the next two parts	uint32
	2. RpcPayloadHeaderProto length	varint
	3. RpcPayloadHeaderProto protobuf serialized message
	4. HadoopRpcRequestProto length	varint
	5. HadoopRpcRequestProto protobuf serialized message
	'''
	protocol = "org.apache.hadoop.hdfs.server.protocol.DatanodeProtocol"

	''' Making of 3, the RPC header '''
	header = RpcPayloadHeader.RpcPayloadHeaderProto()
	#header.rpcKind = RpcPayloadHeader.RPC_WRITABLE
	#header.rpcKind = RpcPayloadHeader.RPC_PROTOCOL_BUFFER
	#header.rpcOp = RpcPayloadHeader.RPC_FINAL_PAYLOAD
	header.rpcKind = 2
	header.rpcOp = 0
	header.callId = self.callid

	# Like writeto delimiter in Java
	''' making of 2 '''
	headerout = header.SerializeToString()
	headerout = encoder._VarintBytes(len(headerout)) + headerout

	self.callbacks[self.callid] = self.RegisterResponse
	self.callid = self.callid + 1

	''' Making of 5 '''
	rpcreq = hadoop_rpc.HadoopRpcRequestProto()
	rpcreq.methodName = "registerDatanode"

	# The data blob in request, need to be filled 
	# later, after creating the blob

	rpcreq.request = ""
	rpcreq.declaringClassProtocolName = protocol
	rpcreq.clientProtocolVersion = 1

	''' Create the blob for registration '''
	proto_data = DatanodeProtocol.RegisterDatanodeRequestProto()
	proto_data.registration.datanodeID.ipAddr = self.nodeinfo.ipAddr
	proto_data.registration.datanodeID.hostName = self.nodeinfo.hostName
	proto_data.registration.datanodeID.storageID = self.storageID
	proto_data.registration.datanodeID.xferPort = self.nodeinfo.xferPort
	proto_data.registration.datanodeID.infoPort = self.nodeinfo.infoPort
	proto_data.registration.datanodeID.ipcPort = self.nodeinfo.ipcPort
	
	'''
	proto_data.StorageInfoProto.layoutVersion = 
	proto_data.StorageInfoProt.namespceID = 
	proto_data.StorageInfoProt.clusterID = 
	proto_data.StorageInfoProt.ctime = 
	'''
	
	proto_data.registration.storageInfo.CopyFrom(self.storageinfo)
	proto_data.registration.keys.isBlockTokenEnabled = False
	proto_data.registration.keys.keyUpdateInterval = 1
	proto_data.registration.keys.tokenLifeTime = 10

	proto_data.registration.keys.currentKey.keyId = 1
	proto_data.registration.keys.currentKey.expiryDate = 2
	proto_data.registration.keys.currentKey.keyBytes = ""

	''' allKeys in the protcol buffer is of type repeated, why ?? '''
	#proto_data.registration.keys.allKeys.keyId = 1
	#proto_data.registration.keys.allKeys.expiryDate = 2 
	#proto_data.registration.keys.allKeys.keyBytes = ""
	proto_data.registration.softwareVersion = self.nodeinfo.version
	
	# Bytes corresponding to blob 
	rpcreq.request = proto_data.SerializeToString()
	
	''' making of 4 '''
	reqout = rpcreq.SerializeToString()
	reqout = encoder._VarintBytes(len(reqout)) + reqout

	''' making of 1 '''
	buf = headerout + reqout
	#print "length : %d" %len(buf)
	self.transport.write(struct.pack(">I", len(buf)))
	self.transport.write(buf)
  
  def BlockReceivedRequest(self, poolID, blockID, genStamp, numBytes, status):


	#print "In BlockReceivedRequest start.................." 
	'''
	Send protcol, write a generic one 
	1. Length of the next two parts	uint32
	2. RpcPayloadHeaderProto length	varint
	3. RpcPayloadHeaderProto protobuf serialized message
	4. HadoopRpcRequestProto length	varint
	5. HadoopRpcRequestProto protobuf serialized message
	'''
	#print "In BlockReceivedRequest.... "
	protocol = "org.apache.hadoop.hdfs.server.protocol.DatanodeProtocol"

	''' Making of 3, the RPC header '''
	header = RpcPayloadHeader.RpcPayloadHeaderProto()
	#header.rpcKind = RpcPayloadHeader.RPC_WRITABLE
	#header.rpcKind = RpcPayloadHeader.RPC_PROTOCOL_BUFFER
	#header.rpcOp = RpcPayloadHeader.RPC_FINAL_PAYLOAD
	header.rpcKind = 2
	header.rpcOp = 0
	header.callId = self.callid

	# Like writeto delimiter in Java
	''' making of 2 '''
	headerout = header.SerializeToString()
	headerout = encoder._VarintBytes(len(headerout)) + headerout

	self.callbacks[self.callid] = self.BlockReceivedResponse
	self.callid = self.callid + 1

	''' Making of 5 '''
	rpcreq = hadoop_rpc.HadoopRpcRequestProto()
	rpcreq.methodName = "blockReceivedAndDeleted"

	# The data blob in request, need to be filled 
	# later, after creating the blob

	rpcreq.request = ""
	rpcreq.declaringClassProtocolName = protocol
	rpcreq.clientProtocolVersion = 1

	buf = DatanodeProtocol.BlockReceivedAndDeletedRequestProto()

	'''
	message BlockReceivedAndDeletedRequestProto {
  	required DatanodeRegistrationProto registration = 1;
	required string blockPoolId = 2;
	repeated StorageReceivedDeletedBlocksProto blocks = 3;
	'''

	buf.registration.CopyFrom(self.datanode_reponse_info)
	buf.blockPoolId = poolID
	blocks_buf = buf.blocks.add()
	blocks_buf.storageID = self.storageID 
	a_storage_blocks = blocks_buf.blocks.add()
	# Receving 
	a_storage_blocks.status = status
	# Received 
	#a_storage_block.status = 2
	a_storage_blocks.block.blockId = blockID
	a_storage_blocks.block.genStamp = genStamp
	a_storage_blocks.block.numBytes= numBytes
	# Bytes corresponding to blob 
	rpcreq.request = buf.SerializeToString()
	
	''' making of 4 '''
	reqout = rpcreq.SerializeToString()
	reqout = encoder._VarintBytes(len(reqout)) + reqout

	''' making of 1 '''
	buf = headerout + reqout
#	print "length : %d" %len(buf)
	self.transport.write(struct.pack(">I", len(buf)))
	self.transport.write(buf)
	print "In BlockReceivedRequest End.................." 
  
  def BlockReceivedResponse(self, message, callid=None):
	#print "In BlockReceivedResponse start.................." 
	pass


  def VersionRequestResponse(self, message, callid=None):
    	print "Message from server"

    	'''
	From hdfs protocol 
	message NamespaceInfoProto {
	required string buildVersion = 1;         // Software revision version (e.g. an svn or git revision)
	required uint32 distUpgradeVersion = 2;   // Distributed upgrade version
	required string blockPoolID = 3;          // block pool used by the namespace
	required StorageInfoProto storageInfo = 4;// Node information
	required string softwareVersion = 5;      // Software version number (e.g. 2.0.0)
	}	
	'''

    	'''
	why do we need to dseralize it again (calling ParseFromString again)
	here as we has done it in the calling function. Becuse we has not 
	desearlized the whole message in the calller but only the partial one ''' 
	response = hdfs.VersionResponseProto()
	response.ParseFromString(message)
	print("Response from namenode for VersionRequest:\n%s" % (str(response)))
	self.storageinfo = hdfs.StorageInfoProto()
	self.storageinfo.CopyFrom(response.info.storageInfo)
	#print("Storage info:\n%s" % (str(self.storageinfo)))

	self.RegisterDataNode()
    
  def connectionMade(self):
        #print("Start of connectionMade")

	### enable keepalive if supported
        try:
            self.transport.setTcpKeepAlive(1)
        except AttributeError: 
		print "KeepAlive not supported"
		pass
        self.transport.setTcpNoDelay(1)
	
	# --- Connection header ---
	# Client.writeConnectionHeader()

	preamble = struct.pack('ccccbbb', 'h', 'r', 'p', 'c', 7, 80, 0)	
	
	'''
	preamble1 = (
            "hrpc"  # Server.HEADER
            "7"    # Server.CURRENT_VERSION
            "P"     # AuthMethod.SIMPLE
            "0"    # Server.IpcSerializationType.PROTOBUF
            )

	'''

	protocol = "org.apache.hadoop.hdfs.server.protocol.DatanodeProtocol"

	# Client.writeConnectionContext()

	context = IpcConnectionContext.IpcConnectionContextProto()
	context.userInfo.effectiveUser = "hduser"
	context.protocol = protocol
	context = context.SerializeToString()

	self.transport.write(preamble)
	self.transport.write(struct.pack(">I", len(context)))
	self.transport.write(context)

	# --- RPC ---
	# Client.sendParam()
	header = RpcPayloadHeader.RpcPayloadHeaderProto()
	#header.rpcKind = RpcPayloadHeader.RPC_WRITABLE
	#header.rpcKind = RpcPayloadHeader.RPC_PROTOCOL_BUFFER
	#header.rpcOp = RpcPayloadHeader.RPC_FINAL_PAYLOAD
	header.rpcKind = 2
	header.rpcOp = 0
	header.callId = self.callid
	self.callbacks[self.callid] = self.VersionRequestResponse
	self.callid = self.callid + 1

	rpcreq = hadoop_rpc.HadoopRpcRequestProto()
	rpcreq.methodName = "versionRequest"
	rpcreq.request = ""
	rpcreq.declaringClassProtocolName = protocol
	rpcreq.clientProtocolVersion = 1

	headerout = header.SerializeToString()
	headerout = encoder._VarintBytes(len(headerout)) + headerout

	reqout = rpcreq.SerializeToString()
	reqout = encoder._VarintBytes(len(reqout)) + reqout
	buf = headerout + reqout
	
	#print "length : %d" %len(buf)

	self.transport.write(struct.pack(">I", len(buf)))
	self.transport.write(buf)
  
  def display_err_msg(self, recv_message):
   
	# Error format Reference: 
	# http://spotify.github.io/snakebite/hadoop_rpc.html
	# https://docs.python.org/2/library/struct.html
	#
	# Length of the Exeption class name	uint32
	# Exception class name	utf-8 string
	# Length of the stack trace	uint32
	# Stack trace	utf-8 string

	buf = struct.unpack(">I", str(recv_message[:4]))
        mlen = int(buf[0])
	class_name = struct.unpack("!b", recv_message[4:4+mlen])
	print "Exception in class::", class_name	

	mlen = 4 + mlen
	buf = struct.unpack(">I", recv_message[mlen:mlen+4])
        mlen1 = int(buf[0])
	stack = struct.unpack("!b", recv_message[mlen+4:mlen+4+mlen1])
	print "Trace is ::\n", stack	

	return 0

  def dataReceived(self, recv_message):

	failed = 0

	# This much data need to be processed, will reset 
	# the value at last if we are able to process 
	# something from here. 

	self.remaining = self.remaining + recv_message

	# stdout.write(data)
	# Decode the data buffer
	# get the object 

	'''
	message RpcResponseHeaderProto {
	  required uint32 callId = 1; // callId used in Request
	  required RpcStatusProto status = 2;
	  optional uint32 serverIpcVersionNum = 3; // in case of an fatal IPC error
	}
	'''

	while len(self.remaining) > 0:
	
		# TBD: Check that at least we got size in the message 
		# varint (not vatint32) may need extra processing
		# http://code.google.com/p/protobuf/source/browse/trunk/
		# python/google/protobuf/internal/decoder.py?r=251

		(size, new_position) = decoder._DecodeVarint(self.remaining,0)
		#print "len_bytes : %d %d" %(size, new_position)

		# get the RPC response header 
		buf = RpcPayloadHeader.RpcResponseHeaderProto()
		buf.ParseFromString(self.remaining[new_position:new_position+size])

		callid = buf.callId
		#print "[%d] In dataRecv for Call id." %(callid)

		'''
		if buf.status == 0:
       		   #print ("Status : Success")
		else:
                   #print ("Status : Failed")
		   failed = 1
		'''

		# Get the size of next block: 
		# Details here: 
		# http://spotify.github.io/snakebite/hadoop_rpc.html#receiving-messages
		
		if (int(new_position + size + 4) <= len(self.remaining)): 
			buf = struct.unpack(">I", self.remaining[new_position + size : new_position + size + 4])
		        mlen = int(new_position + size + 4 + buf[0])
			if mlen <= len(self.remaining):
			    if failed:
				self.display_err_msg(self.remaining[new_position+size+4:])
				return 1
				
		            if callid in self.callbacks:
            			self.callbacks[callid](self.remaining[new_position+size+4:], callid)
          		    else:
          		        self.logger.info("No callback for call %d" % (callid))
			else:
			    return
		else:
		   return

        	self.remaining = self.remaining[mlen:]
		self.callbacks[callid] = None

	# Call the response  	
	#print "Moving ahead"
 	
  def connectionLost(self, reason):
        print "connection lost"
	global keep_running
	#keep_running = 0
	#self.dataxceiver.keep_running = 0
	#self.keep_running = 0

class ThreadClass (threading.Thread):

    def __init__(self, threadID, related_object, client_socket = None, client_addr = None):
        threading.Thread.__init__(self)
        self.threadID = threadID
        self.details = related_object
        self.client_socket = client_socket 
        self.client_addr = client_addr
        self.ret_val = 0

    def run(self):
        related_object = self.details
	if related_object.string == "accept-connections":
	   serv_sock = related_object.sock

	   # Keeps track of all started child threads 
	   child_conn_threads = []
	   child_conn_threads_cnt = 0
	   
	   while keep_running:
	        client_socket, addr = serv_sock.accept()
		#client_socket.settimeout(5.0)

		# Start connection specific thread 
		# We are lossing older context, self.string is 
		# getting overwritten
	
		# Following set of operations should be atomic
		# thread_counter is a shared variable

		related_object.string = "recv-connection-context"
            	t = ThreadClass(child_conn_threads_cnt, related_object, client_socket, addr)
            	child_conn_threads.append(t)
            	child_conn_threads_cnt += 1
            	t.start()
		
	   # TBD : Wait for all child threads to die before closing the server 
	   # socket
	   serv_sock.close()

	elif related_object.string == "start-heartbeat":
	   print "Starting heartbeat thread."
	   while related_object.keep_running:
		if related_object.heartbeat_cnt <= 0:
			related_object.send_heartbeat()
		time.sleep(related_object.heartbeat_interval)

	   print "Exiting heartbeat thread."

	elif related_object.string == "start-blockreport":
	   while related_object.keep_running:
		related_object.send_blockreport()
		time.sleep(related_object.blockreport_interval)

	elif related_object.string == "recv-connection-context":
		print "In recv-connection-context", self.client_socket, self.client_addr
		related_object.process_per_connection_recv(self.client_socket, self.client_addr)

class DataXceiver(object):
	
    # For internal reading: should be larger than bytes_per_chunk
    LOAD_SIZE = 16000.0

    # Op codes
    WRITE_BLOCK = 80
    READ_BLOCK = 81
    READ_METADATA = 82
    REPLACE_BLOCK = 83
    COPY_BLOCK = 84
    BLOCK_CHECKSUM = 85
    TRANSFER_BLOCK = 86

    # Checksum types
    CHECKSUM_NULL = 0
    CHECKSUM_CRC32 = 1
    CHECKSUM_CRC32C = 2
    CHECKSUM_DEFAULT = 3
    CHECKSUM_MIXED = 4

    MAX_READ_ATTEMPTS = 100

    def __init__(self, host, port, datanode):
        self.host, self.port = host, port
	self.max_allowed_conn = 100
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
	self.keep_running = 1
	self.datanode = datanode

    # 0 imples that we don't have sufficient data yet to process. 
    # If sufficient data is avaliable then return the 
    # amount need to process in this pass
    # TBD : We don't need to pass the whole data, just the intial 6 bytes 
    # are sufficient. 

    def check_package_is_complete(self, buf, opcode):

	data_len = len(buf)
	#print "data_len", data_len
        if data_len <= 6:
	   return 0 
	
	if opcode == 80:
	   # We know it is the write operation 
	   # get the size of packet and header
	   # size and we will wait for that much 
	   # length to accumulate 	
	   packet_length = struct.unpack(">i", buf[0:4])[0]
	   header_length = struct.unpack(">h", buf[4:6])[0]
	   print "INFO", "input_data_len:", data_len, "Packet Len:", packet_length, "Header Len:", header_length, "Total Need:", (packet_length + header_length + 6 - 4)
	   #print "INFO", data_len, (packet_length + header_length + 6)
	   if (data_len) < (packet_length + header_length + 6 - 4):
		return 0
		
	elif opcode == 81:
	   return data_len

	return (6 + header_length + packet_length - 4)

    def process_per_connection_recv(self, client_socket, client_addr):

	#print 'Connected from addr ... :', client_addr
        related_object = self
	client_socket.settimeout(5.0)
	data = ""
	stage = 0		
	opcode = None
	seqno = 0
	data_to_process = ""
	while keep_running:
	   try:
		data = ""
		data = client_socket.recv(BUFSIZE)
	   except socket.timeout, e:
		err = e.args[0]
		if err == 'timed out': 
        	    print 'recv timed out, retry later'
		
		    # There is some data pending to process which may 
		    # belong to last request. Check if it is sufficient 
		    # to process.
			
		    if len(data_to_process) == 0:
	            	time.sleep(1)
			continue
		    else:
		    	print "Pending data size is : %d" %len(data_to_process) 
                else:
	            print e
		    break
	   except socket.error, e:
	        # Something else happened, handle error, exit, etc.
	        print e
		break
	   else:
	   	if len(data) == 0 and len(data_to_process):
	           print client_addr, ' Socket closed from client side'
	           break

	   if opcode == None:

			# opcode is None so we are expecting at least 3
			# bytes of data plus the header before we move ahead 
			
			data_to_process = data_to_process + data
			if (len(data_to_process) <= 3):
				continue
			else:
			    data = data_to_process
			    data_to_process = ""

			print "data_to_process", data_to_process
			# Get the header information out 
			client_version = struct.unpack('>h', data[:2])
			#print('Client version is.... : %s' %client_version)
			optype = struct.unpack('b', data[2:3])
			#print('optype is...... : %s' %optype)
			self.client_version = int(client_version[0])
			self.optype = int(optype[0])
			self.addr = client_addr
		
			remaining = data[3:]
			# varint + message, get the size of message out
			(size, new_position) = decoder._DecodeVarint(remaining, 0)
			#print "[Stage : %d] len_bytes : %d %d" %(int(stage), size, new_position)
			opcode = int(optype[0])
			remaining = remaining[new_position:new_position+size]
			stage = 1 
	   else:
			# 0 is incomplete otherwise return the size need to be processed
			data_to_process += data
		     	ret = self.check_package_is_complete(data_to_process, opcode)
		     	if ret == 0:
			     continue

			data = data_to_process[0 : ret]
			data_to_process = data_to_process[ret :]
			print "Go to start processing. Pending data is", opcode, len(data_to_process)
			remaining = data

	   if opcode == 80:
		     #print "1. stage....................................", stage
		     stage = related_object.process_write(remaining, stage, client_socket, self)
		     #print "2. stage....................................", stage
	   elif opcode == 81:
		     #print "1. stage....................................", stage
		     stage = related_object.process_read(remaining, stage, client_socket)
		     #print "2. stage....................................", stage
	   else:
		     print "Operation not supported yet"
		     break 

	client_socket.close()
	return 0

    def create_the_data_and_checksum_buffers():
	pass

    # TBD : self is the dataXeciver object, common across multiple 
    # readers. Need a better design for it so that we can create 
    # per instance data structure. 

    def return_packet(self, filename, client_socket, length, offset, seqno, last_in_block):
	
	data_buffer = ""
	mdata_buffer = ""
	data_bytes = 0
	full_chunks = 0
	partial_chunk = 0

	if last_in_block == False:

		data_fpath = data_dir + filename
		mdata_fpath = data_fpath + ".meta"

		'''
		print "data_fpath", data_fpath
		print "mdata_fpath", mdata_fpath
		'''

		full_chunks = length / chunk_size
		partial_chunks = 0
		if length % chunk_size:
			partial_chunk = 1

		data_fd = open(data_fpath, "r")
		# Seek into the file 
		data_fd.seek(offset)
		mdata_fd = open(mdata_fpath, "r")
		# Caller gives gurantee than offset is chunk boundary aligned
		mdata_fd.seek((offset / chunk_size) * checksum_per_chunk_size)

		# TBD : Seek accordining to offset
		# Can the first chunk be partial, this is possible when 
		# the starting offset is not chunk size aligned. when is
		# this possible ? In that case return the whole packet to 
		# client along with checksum and then let client extract 
		# the right amount of data from there 

		# Assuming here that we are going to read each and every 
		# block starting from offset till length, no fragmented 
		# reads. 

		data_buffer = data_fd.read(full_chunks * chunk_size)
		mdata_buffer = mdata_fd.read(full_chunks * checksum_per_chunk_size)
		data_bytes = (full_chunks * chunk_size)

		# Read the last partial chunk 
		if partial_chunk:
			data_buffer +=  data_fd.read((length - full_chunks * chunk_size))
			data_bytes += (length - full_chunks * chunk_size)
	
			# Checksum is going to eat same amount of space 
			# irrespective of chunk is full or not
			mdata_buffer += mdata_fd.read(checksum_per_chunk_size)

	# Now Create a buffer which we want to send reserver the size at start 
	# which is needed for the metadata
	# Packet length and header length are the first entries in buffer 
	# Write the packet length which is 		
	cksum_bytes = (full_chunks + partial_chunk) * checksum_per_chunk_size
	packet_length = 4 + cksum_bytes + data_bytes 
	packet_header = datatransfer.PacketHeaderProto()
	packet_header.offsetInBlock = offset 
	packet_header.seqno = seqno
	packet_header.lastPacketInBlock = last_in_block
	packet_header.dataLen = data_bytes
	out = packet_header.SerializeToString()
	'''
	print "SerializeToString size : %d" %len(out)
	print "packet_length : %d" %int(packet_length)
	'''
	#header_length = encoder._VarintBytes(len(out))

	# Send the packet, header length and header
	client_socket.send(struct.pack(">i", packet_length))
	#client_socket.send(struct.pack(">h", header_length))
	client_socket.send(struct.pack(">h", len(out)))
	client_socket.send(out)
	client_socket.send(mdata_buffer)
	client_socket.send(data_buffer)

	# Send the last packet in block after reading of the Block
	return 0

    def verify_file_exists(self, filename):
	return 0

    def process_read(self, data, stage, client_socket):
	print "got the read operation..."
	#print ("\n%s" % (hexdump("Msg", data)))
	#print ("\nsize of data %d" %len(str(data)))
	buf = None

	if stage == 1: 
		read_protocol = datatransfer.OpReadBlockProto()
		read_protocol.ParseFromString(data)

		# Get the information: 
		client_ip_header = datatransfer.ClientOperationHeaderProto()
		client_ip_header.CopyFrom(read_protocol.header)

		print "poolID", client_ip_header.baseHeader.block.poolId
		print "blockID", client_ip_header.baseHeader.block.blockId
		'''
		print "generationStamp", client_ip_header.baseHeader.block.generationStamp
		print "numBytes", client_ip_header.baseHeader.block.numBytes
		'''

		if read_protocol.header.baseHeader.HasField('token'):
		   # Display Token information
		   print "Token kind", read_protocol.header.baseHeader.token.kind, read_protocol.header.baseHeader.token.service
		'''
		else:
		   print "No token field"
		'''

		# TBD: Verify that we do have this block present to read 
		filename = str(client_ip_header.baseHeader.block.poolId) + "-" + str(client_ip_header.baseHeader.block.blockId) + "-" + str (client_ip_header.baseHeader.block.generationStamp)
		print "Filename requested...", filename
		ret = self.verify_file_exists(filename)

		# Print Offset and length 
		print "Offset:" , read_protocol.offset
		print "len:" , read_protocol.len
		
	
     		# Return back the ack 
	 	buf = datatransfer.BlockOpResponseProto()
		buf.status = 0

		# Fill the ReadOpChecksumInfoProto
		# TBD : Record these information at time of block write
		# May be in the name itself 

		read_cksum_info = datatransfer.ReadOpChecksumInfoProto()
		read_cksum_info.checksum.type = 2 #CRC32C
		read_cksum_info.checksum.bytesPerChecksum = chunk_size
		read_cksum_info.chunkOffset = 0
		buf.readOpChecksumInfo.CopyFrom(read_cksum_info)
		buf.message = "Response from cacheadvance server"

		# Send the intial information 
		if buf != None:
			out = buf.SerializeToString()
			out = encoder._VarintBytes(len(out)) + out
			client_socket.send(out)

		# Now start creating the data packets and send it to 
		# client 
		lastinblock = False
		
		# Make offset chunk size aligned by rounding it down
		offset_to_start = read_protocol.offset - (read_protocol.offset % chunk_size)
		print "offset_to_start", offset_to_start
		# length to read will increase accordingly
		len_to_read = read_protocol.len + read_protocol.offset % chunk_size
		print "len_to_read", len_to_read
		# Length may be bigger than packet size, break it into packets and then
		# process it

		data_portion_per_packet = max_chunks_per_packet * chunk_size
		full_packets = int(len_to_read / data_portion_per_packet)
		print "full_packets_cnt", full_packets

		if len_to_read % data_portion_per_packet:
			partial_packet = 1
		print "partial_packet_cnt", partial_packet
			
		current_read_offset = offset_to_start
		read_len = max_chunks_per_packet * chunk_size
		seqno = 0
		for i in range(0, full_packets):
			# Ask for a packet size to read 
			print "i", i, "seqno:", seqno, "current_read_offset:", current_read_offset, "read_len:", read_len
			self.return_packet(filename, client_socket, read_len, current_read_offset, seqno, lastinblock)	
			current_read_offset += read_len
			seqno += 1

		# Read any Partial filled packet 
		read_len = len_to_read - full_packets * data_portion_per_packet
		#seqno += 1
		print "seqno:", seqno, "current_read_offset:", current_read_offset, "read_len:", read_len
		self.return_packet(filename, client_socket, read_len, current_read_offset, seqno, lastinblock)	
		current_read_offset += read_len

		lastinblock = True 
		# offset should be the upto last read offset
		# Sequence number should be bumped by 1 
		seqno += 1
		#self.return_packet(filename, client_socket, 0, read_protocol.len + read_protocol.offset, seqno, lastinblock)
		print "seqno:", seqno, "current_read_offset:", current_read_offset, "read_len:", 0
		#self.return_packet(filename, client_socket, read_len, read_len + current_read_offset, seqno, lastinblock)
		self.return_packet(filename, client_socket, read_len, current_read_offset, seqno, lastinblock)
		# TBD : This may be wrong, need to improve this. How do we know that we had reached 
		# the end of the read
		stage = 2

	elif stage == 2:
		(size, new_position) = decoder._DecodeVarint(data, 0)
		proto_buf = datatransfer.ClientReadStatusProto()
		proto_buf.ParseFromString(data[new_position:new_position+size])
		if proto_buf.status == 0:
			print "Client successully able to read the file"
		else:
			print "Client side error ::", protocol.status


	return stage
		
    def record_in_file(self, checksum, data):

	data_filepath = data_dir + self.filename
	if self.data_filefd == None:
	   # Create the file if not exists 
	   # Open the file and record the FD
	   self.data_filefd = open(data_filepath, 'a')
	
	self.data_filefd.write(data)

	# metadata file path
	mdata_filepath = data_filepath + ".meta"
	if self.mdata_filefd == None:
	   # Create the file if not exists 
	   # Open the file and record the FD
	   self.mdata_filefd = open(mdata_filepath, 'a')
	
	self.mdata_filefd.write(checksum)
	return 0

    def generic_recv(self, client_socket, retry = 10):

	client_socket.settimeout(2.0)
	data = ""
	data_to_process = ""
	retry_cnt = 0

	while True:
	   try:
		data = ""
		data = client_socket.recv(BUFSIZE)
	   except socket.timeout, e:
		err = e.args[0]
		if err == 'timed out': 
		    if retry_cnt <= retry:
        	    	#print 'generic_recv recv timed out, retry later:', retry_cnt
	            	time.sleep(1)
			retry_cnt += 1
			continue
		    else:
			break
                else:
	            print e
		    data_to_process = ""
		    break
	   except socket.error, e:
	        # Something else happened, handle error, exit, etc.
	        print e
		data_to_process == ""
		break
	   else:
		if len(data) == 0: # Socket has been closed from other side
			data_to_process = ""
			break

		data_to_process += data
		# If Data is coming then we will keep on retrying for more
		# until we get enough length. Irony is we don't know 
		# how much length we are looking for
		#retry_cnt = 0
		break

	return data_to_process

    def replication_related_processing(self, stage, local_object, data_to_send=None):

	# Create the message and send to the down replication node 
	# to prepare for it, wait for ACK

	if stage == 1:

		# Establish the connection to the given first datanode 
		# and send the client version and opcode first
		
		rep_obj = local_object.rep_obj
		
		# Set the keep ALIVE for this socket
		rep_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		#rep_socket.setTcpKeepAlive(1)
		retry_cnt = 5
		while retry_cnt:
			rep_socket.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
			try:
				rep_socket.connect((local_object.rep_host_ip, local_object.rep_host_port))
				break
			except socket.error, msg:
       				print "Couldnt connect with the socket-server: %s\n terminating program" % msg
				retry_cnt -= 1
				time.sleep(2)
				continue
	
		local_object.rep_socket = rep_socket

		# Get the header information out 
		rep_socket.send(struct.pack('>h',self.client_version))
		rep_socket.send(struct.pack('>b',self.optype))

		# Now send remaining items which is OpWriteBlockProto: 
		'''
		write_protocol = datatransfer.OpWriteBlockProto()
		write_protocol.header.copyFrom(local_object.header)
		write_protocol.source.copyFrom(local_object.source)
		write_protocol.stage = local_object.blockconststage
		if len(local_objects.targets) > 0:
			write_protocol.targets.copyFrom(local_object.targets)		
			write_protocol.pipelineSize = len(local_object.targets)
		
		write_protocol.minBytesRcvd = local_object.minBytesRcvd
		write_protocol.maxBytesRcvd = local_object.maxBytesRcvd
		write_protocol.latestGenerationStamp = local_object.latestGenerationStamp
		'''

		out = rep_obj.SerializeToString()
		out = encoder._VarintBytes(len(out)) + out
		rep_socket.sendall(out)

		# Wait for ACK to be received
		recv_data = self.generic_recv(rep_socket)
		if len(recv_data) == 0:
			print "failed to get ACK from data node:", local_object.rep_host_ip
			# Send the Error to upstream 
		else:
			print "Received data is off size : %d" %len(recv_data)
			print ("\n%s" % (hexdump("Msg", recv_data)))
				

		# Else Process the ACK
		# TBD : Processing for Bad link in downstream 
		(size, new_position) = decoder._DecodeVarint(recv_data,0)
	 	buf = datatransfer.BlockOpResponseProto()
		buf.ParseFromString(recv_data[new_position:new_position+size])
		print "Status from", local_object.rep_host_ip, "is ::", buf.status
		if buf.status != 0:
			print "Error from node:", local_object.rep_host_ip
		
	elif stage == 2:
		# We already have a socket created,
		if local_object.rep_obj == None:
			return 0

		rep_socket = local_object.rep_socket
		try:
			print "replication_related_processing :::", len(data_to_send)
			rep_socket.sendall(data_to_send)
		except socket.error, msg:
       			print "Couldn't send data to the socket-server: %s\n terminating program" % msg
		
		# Wait for ACK to be received
		recv_data = self.generic_recv(rep_socket)
		if len(recv_data) == 0:
			print "failed to get ACK from data node:", local_object.rep_host_ip
			# Send the Error to upstream 
		else:
			print "Received data is off size : %d" %len(recv_data)
			print ("\n%s" % (hexdump("Msg", recv_data)))
		
			buf = datatransfer.PipelineAckProto()
			(size, new_position) = decoder._DecodeVarint(recv_data,0)
			buf.ParseFromString(recv_data[new_position:new_position+size])
			print "ACK for seqno...................... :", buf.seqno, "status", buf.status[0]
			#local_object.pipeline_results.append(buf.status)
			if buf.status[0] != 0:
				print "Write failed on downstream node"
	else:
		pass

	return 0

    def process_write(self, data, stage, client_socket, local_object):
	#print "In write code path"
	#print ("\n%s" % (hexdump("Msg", data)))
	#print ("\nsize of data %d" %len(str(data)))
	buf = None

	if stage == 1: 
		write_protocol = datatransfer.OpWriteBlockProto()
		write_protocol.ParseFromString(data)

		# Get the information: 
		client_ip_header = datatransfer.ClientOperationHeaderProto()
		client_ip_header.CopyFrom(write_protocol.header)

		print "poolID", client_ip_header.baseHeader.block.poolId
		print "blockID", client_ip_header.baseHeader.block.blockId
		'''
		print "generationStamp", client_ip_header.baseHeader.block.generationStamp
		print "numBytes", client_ip_header.baseHeader.block.numBytes
		'''

		# Storage it so that we can use later 
		self.poolID = client_ip_header.baseHeader.block.poolId
		self.blockID = client_ip_header.baseHeader.block.blockId
		self.genStamp = client_ip_header.baseHeader.block.generationStamp
		self.numBytes = 0

		# DatanodeInfoProto
		# A regular array,

		'''
		target_cnt = len(write_protocol.targets)
		'''
		# TBD : Used for creating replication pipeline
		target = ""
		target_list = []
		for target in write_protocol.targets:
			print "target", target
			target_list.append(target) 
			
		print "target_cnt", len(target_list)

		if write_protocol.HasField('source'):
		   datainfo_source = hdfs.DatanodeInfoProto()
		   datainfo_source.CopyFrom(write_protocol.source)
		   print "datainfo_source capacity %d:" %(datainfo_source.capacity)
		   local_object.got_source = 1
		else:
		   print "No source field"
		   local_object.got_source = 0

		# PIPELINE_SETUP_CREATE
		print "write_protocol.pipelineSize::", write_protocol.pipelineSize
		if write_protocol.pipelineSize > 1 and write_protocol.stage == 6:
		
			rep_obj = datatransfer.OpWriteBlockProto()
			rep_obj.header.CopyFrom(write_protocol.header)
			rep_obj.stage = write_protocol.stage;
			rep_obj.pipelineSize = write_protocol.pipelineSize - 1;
  			rep_obj.minBytesRcvd = write_protocol.minBytesRcvd;
  			rep_obj.maxBytesRcvd = write_protocol.maxBytesRcvd;
  			rep_obj.latestGenerationStamp = write_protocol.latestGenerationStamp;
			rep_obj.requestedChecksum.CopyFrom(write_protocol.requestedChecksum)
			
			local_object.rep_host_ip = target_list[0].id.ipAddr
			local_object.rep_host_port = target_list[0].id.xferPort
			print "rep_obj.rep_host_ip", local_object.rep_host_ip
			print "rep_obj.rep_host_port", local_object.rep_host_port
			first_entry = 1
			for remaining_target in target_list[0:]:
				if first_entry:
					rep_obj.source.CopyFrom(remaining_target)
					first_entry = 0
				else:
					target = rep_obj.targets.add()
					target.CopyFrom(remaining_target)

			local_object.rep_obj = rep_obj
			local_object.pipeline_results = []
			self.replication_related_processing(stage, local_object)
		else:
			# This node is not involved in pipelining 
			local_object.pipeline_results = []
			local_object.rep_obj = None 
		
		print "BlockConstructionStage", write_protocol.stage
		print "pipelineSize", write_protocol.pipelineSize
		print "minBytesRcvd", write_protocol.minBytesRcvd
		print "maxBytesRcvd", write_protocol.maxBytesRcvd
		print "latestGenerationStamp", write_protocol.latestGenerationStamp
		print "checksum type", write_protocol.requestedChecksum.type
		print "bytesPerChecksum", write_protocol.requestedChecksum.bytesPerChecksum
		self.bytesperchecksum = write_protocol.requestedChecksum.bytesPerChecksum
	
		# Create the file name
		self.filename = str(self.poolID) + "-" + str(self.blockID) + "-" + str(self.genStamp)
		self.data_filefd = None
		self.mdata_filefd = None

		# TBD : We need to inform Name node that We are getting the file 
		# ReceivedDeletedBlockInfoProto

     		# Return back the ack with SUCCESS to client
	 	buf = datatransfer.BlockOpResponseProto()
		buf.status = 0
		stage = 2
		if buf != None:
			print "sending ACK to", local_object.addr
			out = buf.SerializeToString()
			out = encoder._VarintBytes(len(out)) + out
			client_socket.send(out)

	elif stage == 2:

		# First send the data to the lower layer 
		# and wait for it's ACK before start processing the 
		# on the local node

		self.replication_related_processing(stage, local_object, data)

		# Got the data 
		# 4 byte integer representing the packet size 
		# Followed by 2-bytes short representing the header 
		# length 

		packet_length = struct.unpack(">i", data[0:4])[0]
		header_length = struct.unpack(">h", data[4:6])[0]
		'''
		print "packet_length", packet_length
		print "header_length", header_length
		'''

		packet_header = datatransfer.PacketHeaderProto()
		packet_header.ParseFromString(data[6:6 + int(header_length)])

		print "Request for seqno:offset ....", packet_header.seqno, packet_header.offsetInBlock
		print "offsetInBlock", packet_header.offsetInBlock, "DataLen:", packet_header.dataLen
		'''
		print "lastPacketInBlock", packet_header.lastPacketInBlock
		print "dataLen", packet_header.dataLen
		'''

		if packet_header.lastPacketInBlock == False:
			# This is given , 
			#int pktLen = HdfsConstants.BYTES_IN_INTEGER + dataLen + checksumLen;
			checksumLen = packet_length - 4 - packet_header.dataLen
			checksum_start = 6 + int(header_length)
			data_start = checksum_start + checksumLen	
			dataLen = packet_header.dataLen

			'''
			print "checksumLen", checksumLen
			print "checksum_start", checksum_start
			'''
		
			# get the number of chucks in package 
			if (packet_header.dataLen < self.bytesperchecksum):
				full_chunks_cnt = 0
			else:
				full_chunks_cnt = packet_header.dataLen / self.bytesperchecksum 
		
			partial_chunk_cnt = 0
			if packet_header.dataLen % self.bytesperchecksum:
				partial_chunk_cnt = 1 

			# Full or partial chuck, it should not affet the number of bytes 
			# required to store the checksum
			checksum_rec_length = checksumLen / (full_chunks_cnt + partial_chunk_cnt) 
		
			# Read the checksum array
			#checksum_str =	datatransfer.ChecksumProto()
			#checksum_str.ParseFromString(data[checksum_start:checksum_start+checksumLen])

			# TBD : Verify this data and checksum originzation. Some of the documents are 
			# saying that, metafile is for holding the version,cecksum type and bytesperchecksum
			# information where chunk information (512 bytes data + 4 bytes checksum) is part 
			# of datafile itself
			# Reference: Simple beauty HDFS write file Process Analysis


			for i in range(0, full_chunks_cnt):
			    # Last record which may be partial one, will be read outside this loop
			    '''
			    print ("checksum:", data[checksum_start + i * checksum_rec_length : 
						checksum_start + (i+1)*checksum_rec_length])
			    print ("data:", data[data_start + i * self.bytesperchecksum : 
					data_start + (i+1) * self.bytesperchecksum])
			    '''
			   
			    to_record_checksum = data[checksum_start + i * checksum_rec_length : checksum_start + (i+1)*checksum_rec_length]
			    to_record_data = data[data_start + i * self.bytesperchecksum : data_start + (i+1) * self.bytesperchecksum]
			    self.record_in_file(to_record_checksum, to_record_data)

			if partial_chunk_cnt:
			    remaining_data_len = dataLen - full_chunks_cnt * self.bytesperchecksum
			    '''
			    print ("checksum:", data[checksum_start + full_chunks_cnt * checksum_rec_length : 
					checksum_start + (full_chunks_cnt + 1)*checksum_rec_length])
			    print ("data:", data[data_start + full_chunks_cnt * self.bytesperchecksum : 
					data_start + (full_chunks_cnt) * self.bytesperchecksum + remaining_data_len])
		            '''

			    to_record_checksum = data[checksum_start + full_chunks_cnt * checksum_rec_length : checksum_start + (full_chunks_cnt + 1)*checksum_rec_length]
			    to_record_data = data[data_start + full_chunks_cnt * self.bytesperchecksum : data_start + (full_chunks_cnt) * self.bytesperchecksum + remaining_data_len]
			    self.record_in_file(to_record_checksum, to_record_data)

			stage = 2
			# Inform Namenode first about this new block (Reciving)
			self.numBytes += dataLen
			self.datanode.datanodeprotocol.BlockReceivedRequest(self.poolID, self.blockID, self.genStamp, self.numBytes, 1)

			'''
     			# Create buffer for ACK 
		 	buf = datatransfer.BlockOpResponseProto()
			buf.message = "Response from CA datanode......"
			buf.status = 0
			'''

			buf = datatransfer.PipelineAckProto()
			buf.seqno = packet_header.seqno
			print "ACK for seqno...................... :", buf.seqno
			buf.status.append(0)
			'''
			if len(local_object.pipeline_results):
				buf.status.append(local_object.pipeline_results)
			'''
			
			if buf != None:
				out = buf.SerializeToString()
				out = encoder._VarintBytes(len(out)) + out
				client_socket.send(out)
		else:
			# End of this packet 
			# Send the block information to the name node
			# Not sure about connection but we can keep it, I guess
		
			stage = 2 
			buf = datatransfer.PipelineAckProto()
			buf.seqno = packet_header.seqno
			print "Last Packet in the block, ACK for seqno...................... :", buf.seqno
			buf.status.append(0)
			if buf != None:
				out = buf.SerializeToString()
				out = encoder._VarintBytes(len(out)) + out
				client_socket.send(out)
			
			if self.data_filefd != None:
				#os.sync(self.data_filefd)
				self.data_filefd.close()
				self.data_filefd = None

			if self.mdata_filefd != None:
				#os.sync(self.mdata_filefd)
				self.mdata_filefd.close()
				self.mdata_filefd = None

			print "Response from CA datanode......"
			# Inform Namenode first about this new block (Received)
			self.datanode.datanodeprotocol.BlockReceivedRequest(self.poolID, self.blockID, self.genStamp, self.numBytes, 2)
			if local_object.got_source == 0:
				print "Final ACK to the client. local_object.got_source", local_object.got_source
				# Create buffer for ACK 
			 	buf = datatransfer.BlockOpResponseProto()
				buf.message = "Response from CA datanode......"
				buf.status = 0
				if buf != None:
					out = buf.SerializeToString()
					out = encoder._VarintBytes(len(out)) + out
					client_socket.send(out)

	return stage

    def accept_connections(self):
        try:

	    ''' Create a seperate thread for this'''
	    ADDR=(self.host, self.port)
	    self.sock.bind(ADDR)
	    self.sock.listen(self.max_allowed_conn)
	    global thread_counter 
	    global threads
	    '''
	    try:
	    '''
	    self.string = "accept-connections"
            t = ThreadClass(thread_counter, self)
            threads.append(t)
            thread_counter += 1
            t.start()
	    '''
            except:
               print("%s failed" % self)
               sys.exit(1)
	    '''

            return True
        except Exception:
            print("%s Failed to start connection to DataNode" % self)
            return False

    def __repr__(self):
        return "Starting DataXceiver service on %s:%d" % (self.host, self.port)

class DataNodeFactory(ClientFactory):

  def __init__(self, storageID, nodeinfo, dataxceiver= None):
       self.storageID = storageID
       self.nodeinfo = nodeinfo
       #self.dataxceiver = dataxceiver
       self.datanodeprotocol = None
       self.logger = None

  def startedConnecting(self, connector):
	print "Oppening connection"

  def clientConnectionFailed(self, connector, reason):
        print "Connection failed - goodbye! %s" %reason
        reactor.stop()
    
  def buildProtocol(self, addr):
    print('Started connecting')
    #p = DatanodeClientProtocol(self.storageID , self.nodeinfo, self.dataxceiver)
    p = DatanodeClientProtocol(self.storageID , self.nodeinfo)
    self.datanodeprotocol = p
    return p

def usage():
    print "usage: datanode.py <datanode_conf_file>"
    print ("datanode_conf_file needs to contain the values"
	    " of all the following parameters::\nnamenode_name\n"
	    "datanode_name\nnamenode_port\ndatanode_xferport\n"
	    "datanode_infoport\ndatanode_ipcport\ndatanode_dir\nStorageID")

    sys.exit(1)

if __name__ == "__main__":
    try:
        if ("--help") in sys.argv[1:]:
            usage()

        elif ("-h") in sys.argv[1:]:
            usage()

    except KeyboardInterrupt:
        sys.exit(1)

    if len(sys.argv) != 2:
	usage()

    conf_file = sys.argv[1]
    if not os.path.exists(conf_file):
	print "File %s does not exist" %conf_file
        sys.exit(1)
	
    lines = open(conf_file).readlines()
    configuration = {}
    print "Reading conf file..."
    for line in lines:
	line = line.strip("\n")
	if line.startswith("#"):
  	  continue
	key, value = line.split("=")
	if value:
	   configuration [key] = value

    # We are looking for 8 parameters to be defined by user now in the conf file 
    # TBD : Need to read these from hadoop XML conf files 
    if len(configuration) != len(user_defined_params): 
	    usage()
	    sys.exit(1)

    # Get the name to IP mapping for namenode and datanodes
    ip = socket.gethostbyname(configuration['namenode_name'])
    if ip:
	configuration['namenode_ip'] = ip
    else:
	print ("Unable to get the IP address for name %s." 
		" Please make sure you have corresponding" 
		" entry in either /etc/hosts or DNS server."  
		%(configuration['namenode_name']))

	sys.exit(1)

    socket.gethostbyname(configuration['datanode_name'])
    if ip:
	configuration['datanode_ip'] = ip
    else:
	print ("Unable to get the IP address for name %s." 
		" Please make sure you have corresponding" 
		" entry in either /etc/hosts or DNS server."  
		%(configuration['datanode_name']))

	sys.exit(1)

    # datanode data dir
    data_dir = "%s" %configuration['datanode_dir']
    if not os.path.exists(data_dir):
	print "Datanode datadir %s does not exist. Please create it first" %data_dir
        sys.exit(1)

    capacity = get_free_capacity(data_dir)
    configuration ['datadir_capacity'] = int(capacity)
    print "Configuration ::", configuration, "\n"


    namenodeport = int(configuration['namenode_port'])
    namenode = configuration['namenode_name']
    sid = configuration['StorageID']

    print ("Registering Datanode with StorageID %s" % (sid))
    ni = Node(configuration)
    dn = DataNodeFactory(sid, ni)

    # Start DataXceiver service for IOs
    daxc = DataXceiver(ni.ipAddr, ni.xferPort, dn)
    ret = daxc.accept_connections()
    if ret == False:
	print ("Unable to start the DataXceiver. This may be because" 
	   	" an instance of datanode is already running. Plese stop" 
		" the running instance and try again")
	sys.exit(1)

    # Start IPC service
    connector = reactor.connectTCP(namenode, namenodeport, dn)
    reactor.run()
    connector.disconnect()
