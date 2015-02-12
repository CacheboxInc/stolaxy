1. Before starting the nodename, please create a conf file with following parameters: 

# Make sure name to IP mapping must be resolved either by dns or through /etc/hosts lookup
namenode_name=namenode.cachebox.com
datanode_name=datanode1.cachebox.com
namenode_port=10000
datanode_xferport=50010
datanode_infoport=50011
datanode_ipcport=50012
# Absolute path of datanode_dir, where you want to store data files
datanode_dir=/home/hduser/datanode/
#uuidgen command's output can be used as StorageID
StorageID=d6fa1dae-81c2-4ff2-8cd7-e9dec90e3602

2. Make sure that namenode service is running. "jps" command on namename server can give you list of running services. All the testing has been performaned on the hadoop version hadoop-2.0.1-alpha (Protocol version 7/8), the package can be downloaded from this location.  
https://archive.apache.org/dist/hadoop/core/hadoop-2.0.1-alpha/

3. Start datanode service with following command:
python datanode.py <conf_file>

datanode will start running in foreground, it has not be daemonized yet. 

4. To start multiple datanodes, repeate steps 1-3 on the all nodes where you want to start the datanode service. 

5. To test, you can try with following commands: 
hadoop fs -copyFromLocal /boot/grub/grub.cfg /
hadoop fs -mkdir /test
hadoop fs -copyFromLocal /etc/passwd /test
hadoop fs -ls /
hadoop fs -cat /grub.cfg
hadoop fs -cat /test/passwd

 


