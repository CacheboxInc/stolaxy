import argparse

parser = argparse.ArgumentParser()

parser.add_argument("-a", "--addr", action="store", dest="addr",
                    help="address for the node")
parser.add_argument("-p", "--port", action="store", dest="port", type=int,
                    help="port for the node")
parser.add_argument("-b", "--boot", action="store", dest="bootstrap",
                    help="address:port tuple for the bootstrap peer")
parser.add_argument("-o", "--objectname", action="store", dest="objectname", default='',
                    help="client object dotted name")
parser.add_argument("-l", "--logger", action="store", dest="logger", default='',
                    help="logger address")
parser.add_argument("-n", "--domainname", action="store", dest="domain", default='',
                    help="domain name that the nameserver will accept queries for")
parser.add_argument("-r", "--route53", action="store_true", dest="route53", default=False,
                    help="use Route53 (requires a Route53 zone)")
parser.add_argument("-w", "--writetodisk", action="store_true", dest="writetodisk", default=False,
                    help="writing to disk on/off")
parser.add_argument("-d", "--debug", action="store_true", dest="debug", default=False,
                    help="debug on/off")
parser.add_argument("-e", "--export", action="store", dest="export", default='/tmp',
                    help="path to export")
args = parser.parse_args()
