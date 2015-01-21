from cmd import Cmd
import getopt
import sys

from configdb import session
from hadoop import create_mapreduce

APP_TYPES = ('mapreduce', 'hbase', 'impala', 'spark')
APP_TYPES_STRING = '|'.join(APP_TYPES)

class StolaxyCmd(Cmd):

    intro = """Stolaxy Big Data Platform Manager. Cachebox Inc (c) 2015.\n
? for help
quit to quit.
"""

    prompt = "stolaxy> "

    def do_help(self, x):
        print 'available commands:'
        print 'create'
        print 'list'

    def do_list(self, x):
        x = x.split()
        if len(x) == 0:
            print 'nodes ...'
            return

    def do_create(self, x):
        x = x.split()
        
        def help():
            print 'create app <%s> <app_name>' % APP_TYPES_STRING
            print 'create host <ipaddress>'

        if len(x) == 0:
            help()
            return

        try:
            if x[0] == 'app':
                apptype = x[1]
                if apptype not in APP_TYPES:
                    help()
                    return

                if apptype == 'mapreduce':
                    create_mapreduce(name = x[2])

            else:
                help()
                return
        except:
            help()

        return

    def do_quit(self, x):
        sys.exit(0)

def main():
    Cmd.cmdloop(StolaxyCmd())

if __name__ == '__main__':
    main()
