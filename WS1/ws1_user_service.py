from flask import Flask 
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Boolean, Iterable, ComplexModel, Fault
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication 
from werkzeug.middleware.dispatcher import DispatcherMiddleware 
import os 


from db_utils import (
    db_user_login, db_user_register, db_list_packages,
    db_check_status, db_search_packages
)


class PackageInfo(ComplexModel):
    _type_info = [('id', Integer), ('name', Unicode), ('description', Unicode), ('sender_city', Unicode), ('destination_city', Unicode), ('is_tracked', Boolean)]
class TrackingStatus(ComplexModel):
     _type_info = [('city', Unicode), ('timestamp', Unicode)]
class UserInfo(ComplexModel):
     _type_info = [('user_id', Integer), ('username', Unicode), ('role', Unicode)]



class UserService(ServiceBase):
    @rpc(Unicode, Unicode, _returns=UserInfo)
    def login(ctx, username, password):
        if not username or not password: raise Fault(faultcode='Client', faultstring='Username and password are required.')
        user_data = db_user_login(username, password)
        if user_data: return UserInfo(user_id=user_data['user_id'], username=username, role=user_data['role'])
        else: raise Fault(faultcode='Client', faultstring='Invalid credentials.')

    @rpc(Unicode, Unicode, Unicode, _returns=Boolean)
    def register(ctx, username, password, email):
        if not username or not password or not email: raise Fault(faultcode='Client', faultstring='Username, password, and email are required.')
        success = db_user_register(username, password, email)
        if not success: raise Fault(faultcode='Client', faultstring='Registration failed. Username or email might already exist.')
        return success

    @rpc(Integer, _returns=Iterable(PackageInfo))
    def listPackages(ctx, user_id):
        if user_id is None: raise Fault(faultcode='Client', faultstring='User ID is required.')
        packages_data = db_list_packages(user_id)
        return [PackageInfo(**pkg) for pkg in packages_data]

    @rpc(Integer, Unicode, _returns=Iterable(PackageInfo))
    def searchPackages(ctx, user_id, search_term):
        if user_id is None: raise Fault(faultcode='Client', faultstring='User ID is required.')
        if search_term is None: search_term = ""
        packages_data = db_search_packages(user_id, search_term)
        return [PackageInfo(**pkg) for pkg in packages_data]

    @rpc(Integer, _returns=Iterable(TrackingStatus))
    def checkStatus(ctx, package_id):
        if package_id is None: raise Fault(faultcode='Client', faultstring='Package ID is required.')
        status_data = db_check_status(package_id)
        return [TrackingStatus(**status) for status in status_data]



flask_app = Flask(__name__) 


spyne_app = Application([UserService],
    tns='sds.lab.user.v1',
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)

spyne_wsgi_app = WsgiApplication(spyne_app)

flask_app.wsgi_app = DispatcherMiddleware(flask_app.wsgi_app, {
    '/ws1': spyne_wsgi_app
})

@flask_app.route('/health')
def health_check():
    return "WS1 OK", 200

if __name__ == '__main__':
    flask_app.run(host='0.0.0.0', port=5001, debug=os.environ.get("FLASK_DEBUG", "0") == "1")