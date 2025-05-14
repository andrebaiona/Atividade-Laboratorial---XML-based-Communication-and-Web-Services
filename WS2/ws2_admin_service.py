from flask import Flask 
from spyne import Application, rpc, ServiceBase, Unicode, Integer, Boolean, Iterable, ComplexModel, Fault, DateTime
from spyne.protocol.soap import Soap11
from spyne.server.wsgi import WsgiApplication 
from werkzeug.middleware.dispatcher import DispatcherMiddleware 
import os
from datetime import datetime


from db_utils import (
    db_add_package, db_remove_package, db_register_tracking,
    db_update_package_status, db_get_all_users, db_get_all_packages
)


class PackageInfoAdmin(ComplexModel): 
    _type_info = [
        ('id', Integer),
        ('name', Unicode),
        ('description', Unicode),
        ('sender_city', Unicode),
        ('destination_city', Unicode),
        ('is_tracked', Boolean),
        ('sender_username', Unicode),
        ('receiver_username', Unicode),
        ('creation_date', Unicode), 
    ]

class UserSelectionInfo(ComplexModel): 
     _type_info = [
         ('id', Integer),
         ('username', Unicode),
     ]

class AdminService(ServiceBase):

    @rpc(_returns=Iterable(UserSelectionInfo))
    def getAllUsers(ctx):
         """Retorna lista de utilizadores para seleção."""
         users_data = db_get_all_users()
         return [UserSelectionInfo(**user) for user in users_data]

    @rpc(_returns=Iterable(PackageInfoAdmin))
    def getAllPackages(ctx):
         """Retorna lista de todos os pacotes no sistema."""
         packages_data = db_get_all_packages()
         return [PackageInfoAdmin(**pkg) for pkg in packages_data]

    @rpc(Integer, Integer, Unicode, Unicode, Unicode, Unicode, _returns=Integer)
    def addPackage(ctx, sender_id, receiver_id, name, description, sender_city, destination_city):
        """Adiciona um novo pacote. Retorna o ID do novo pacote ou Fault."""
        if not all([sender_id, receiver_id, name, sender_city, destination_city]):
            raise Fault(faultcode='Client', faultstring='Missing required package information (sender_id, receiver_id, name, sender_city, destination_city).')
        new_id = db_add_package(sender_id, receiver_id, name, description, sender_city, destination_city)
        if new_id is None:
            raise Fault(faultcode='Server', faultstring='Failed to add package. Please check user IDs and database connection.')
        return new_id

    @rpc(Integer, _returns=Boolean)
    def removePackage(ctx, package_id):
        """Remove um pacote pelo ID."""
        if package_id is None or package_id <= 0:
             raise Fault(faultcode='Client', faultstring='A valid Package ID is required.')
        success = db_remove_package(package_id)
        if not success:
             raise Fault(faultcode='Client', faultstring=f'Failed to remove package {package_id}. It might not exist.')
        return success

    @rpc(Integer, Unicode, DateTime, _returns=Boolean)
    def registerPackageTracking(ctx, package_id, initial_city, initial_time):
        """Marca um pacote como rastreado e adiciona o ponto inicial."""
        if not all([package_id, initial_city, initial_time]):
             raise Fault(faultcode='Client', faultstring='Package ID, initial city, and initial time (DateTime) are required.')
        if package_id <= 0:
             raise Fault(faultcode='Client', faultstring='Invalid Package ID.')

        success = db_register_tracking(package_id, initial_city, initial_time.isoformat())
        if not success:
             raise Fault(faultcode='Server', faultstring=f'Failed to register tracking for package {package_id}. Package might not exist or is already tracked.')
        return success

    @rpc(Integer, Unicode, DateTime, _returns=Boolean)
    def updatePackageStatus(ctx, package_id, city, time):
        """Adiciona uma nova entrada de rastreamento a um pacote."""
        if not all([package_id, city, time]):
            raise Fault(faultcode='Client', faultstring='Package ID, city, and time (DateTime) are required.')
        if package_id <= 0:
             raise Fault(faultcode='Client', faultstring='Invalid Package ID.')

        success = db_update_package_status(package_id, city, time.isoformat())
        if not success:
            raise Fault(faultcode='Server', faultstring=f'Failed to update status for package {package_id}. Package might not exist or is not tracked.')
        return success


flask_app = Flask(__name__) 


spyne_app = Application([AdminService],
    tns='sds.lab.admin.v1', 
    in_protocol=Soap11(validator='lxml'),
    out_protocol=Soap11()
)


spyne_wsgi_app = WsgiApplication(spyne_app)


flask_app.wsgi_app = DispatcherMiddleware(flask_app.wsgi_app, {
    '/ws2': spyne_wsgi_app
})

@flask_app.route('/health')
def health_check():
    return "WS2 OK", 200

if __name__ == '__main__':
    debug_mode = os.environ.get("FLASK_DEBUG", "0") == "1"
    flask_app.run(host='0.0.0.0', port=5002, debug=debug_mode)