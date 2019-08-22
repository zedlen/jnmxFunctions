from os import getenv
import pymysql
from pymysql.err import OperationalError
from google.cloud import storage
import tempfile
import numpy
import face_recognition
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True

CONNECTION_NAME = getenv(
  'INSTANCE_CONNECTION_NAME',
  'localhost')
DB_USER = getenv('MYSQL_USER', 'root')
DB_PASSWORD = getenv('MYSQL_PASSWORD', 'jurisnova@2019')
DB_NAME = getenv('MYSQL_DATABASE', 'jurisnova')

mysql_config = {
  'user': DB_USER,
  'password': DB_PASSWORD,
  'db': DB_NAME,
  'charset': 'utf8mb4',
  'cursorclass': pymysql.cursors.DictCursor,
  'autocommit': True
}

# Create SQL connection globally to enable reuse
# PyMySQL does not include support for connection pooling
mysql_conn = None

def __get_cursor():
    """
    Helper function to get a cursor
      PyMySQL does NOT automatically reconnect,
      so we must reconnect explicitly using ping()
    """
    try:
        return mysql_conn.cursor()
    except OperationalError:
        mysql_conn.ping(reconnect=True)
        return mysql_conn.cursor()

def validate(request):
    global mysql_conn

    # Initialize connections lazily, in case SQL access isn't needed for this
    # GCF instance. Doing so minimizes the number of active SQL connections,
    # which helps keep your GCF instances under SQL connection limits.
    if not mysql_conn:
        try:
            mysql_conn = pymysql.connect(**mysql_config)
        except OperationalError:
            # If production settings fail, use local development ones
            mysql_config['unix_socket'] = f'/cloudsql/{CONNECTION_NAME}'
            mysql_conn = pymysql.connect(**mysql_config)

    # Remember to close SQL resources declared while running this function.
    # Keep any declared in global scope (e.g. mysql_conn) for later reuse.
    with __get_cursor() as cursor:
        sql = "SELECT u.photos_path, u.user_id, ui.file_name, ui.image_type FROM `users_info` u JOIN users_image ui ON ui.user_id=u.user_id WHERE `is_valid`=%s and validated=0;"
        cursor.execute(sql, (0,))
        results = cursor.fetchall()        
        no_validated_users = []
        for result in results:
            found = False
            for user in no_validated_users:
                if user['user_id'] == result['user_id']:
                    user[result['image_type']] = result['file_name']
                    found = True
            if found is False:
                no_validated_users.append({
                    'user_id': result['user_id'],
                    result['image_type']: result['file_name'],
                    'path': result['photos_path']           
                })
        storage_client = storage.Client()
        for user in no_validated_users:            
            #face_file = storage_client.bucket('jurisnovamx').blob(user['photos_path']+'initial_photo.png')
            #print(face_file)
            with tempfile.NamedTemporaryFile(mode="wb") as jpg:
                storage_client.download_blob_to_file('gs://jurisnovamx.appspot.com/'+user['path']+user['INITIAL_PHOTO'], jpg)
                face_photo = face_recognition.load_image_file(jpg.name)
            face_photo_encoding = face_recognition.face_encodings(face_photo)[0]
            
            #id_file = storage_client.bucket('jurisnovamx').blob(user['photos_path']+'initial_id_photo.png')
            #print(id_file)
            with tempfile.NamedTemporaryFile(mode="wb") as jpg:
                storage_client.download_blob_to_file('gs://jurisnovamx.appspot.com/'+user['path']+user['INITIAL_ID_PHOTO'], jpg)
                id_face_photo = face_recognition.load_image_file(jpg.name)
            id_face_photo_encoding = face_recognition.face_encodings(id_face_photo)[0]
            dist = numpy.linalg.norm(face_photo_encoding-id_face_photo_encoding)
            dist = 1-dist
            if dist>.50:
                print('validated')
                # TODO: Validated it doestn match to other user model
                # TODO: Create user model
            else:
                print('no face match with id')
                # TODO: Notify user photos where no validated                

        return 'ok'


validate(None)