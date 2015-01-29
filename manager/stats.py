from configdb import *

configuration = session.query(DBConfiguration).one()
print (configuration)

groups = session.query(DBGroup).all()
for group in groups:
    print(group)

users = session.query(DBUser).all()
for user in users:
    print(user)

hosts = session.query(DBPhysicalHost).all()
for host in hosts:
    print(host)

datastores = session.query(DBDatastore).all()
for datastore in datastores:
    print(datastore)

applications = session.query(DBApplication).all()
for app in applications:
    print(app)


vnodes = session.query(DBVirtualNode).all()
for vnode in vnodes:
    print(vnode)
