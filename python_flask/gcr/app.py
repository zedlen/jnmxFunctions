from flask import Flask, jsonify, make_response
from os import getenv
import pymysql
from pymysql.err import OperationalError
from google.cloud import storage
import tempfile
import numpy
import face_recognition
import json
import hashlib
from PIL import ImageFile
ImageFile.LOAD_TRUNCATED_IMAGES = True
app = Flask(__name__)

CONNECTION_NAME = getenv(
    'INSTANCE_CONNECTION_NAME',
    #'34.67.179.36'
    'localhost'
)
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


@app.route('/')
def hello_world():
    return make_response(jsonify({'success': True,'msg':"Let's Rock \m/...(>.<)…\m/"}), 200)

@app.route('/faceMatchID/<id>')
def faceMatchID(id):
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

        #request_json = request.get_json(silent=True)
        #if request_json and 'user_id' in request_json:
        #    name = request_json['user_id']
        #else:
        #    raise ValueError("JSON is invalid, or missing a 'user_id' property")
        print(id)
        sql = '''SELECT 
            u.photos_path, 
            u.user_id, 
            ui.file_name, 
            ui.image_type,
            au.username  
        FROM `users_info` u 
        JOIN users_image ui 
        ON 
            ui.user_id=u.user_id 
        JOIN auth_user au
        ON
            au.id = u.user_id
        WHERE 
            `is_valid` = 0
            AND  u.user_id = {} 
            AND ui.validated = 0;'''.format(id)        
        try:
            cursor.execute(sql)
            results = cursor.fetchall()        
        except Exception as e:
            return make_response(jsonify({'success': False,'msg':'{}'.format(e)}), 500)
        finally:
            cursor.close()
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
                'path': result['photos_path'],
                'username': result['username']           
            })
    storage_client = storage.Client()
    for user in no_validated_users:            
        
        try:
            with tempfile.NamedTemporaryFile(mode="wb") as jpg:
                storage_client.download_blob_to_file('gs://jurisnovamx.appspot.com/'+user['path']+user['INITIAL_PHOTO'], jpg)
                face_photo = face_recognition.load_image_file(jpg.name)
            face_photo_encoding_list = face_recognition.face_encodings(face_photo)
            if len(face_photo_encoding_list) > 1:
                return make_response(jsonify({'success':False,'error': 'More than one face found in photo'}),400)    
            face_photo_encoding = face_photo_encoding_list[0]
        except:
            return make_response(jsonify({'success':False,'error': 'No face found in photo'}),400)
        
        try:
            with tempfile.NamedTemporaryFile(mode="wb") as jpg:
                storage_client.download_blob_to_file('gs://jurisnovamx.appspot.com/'+user['path']+user['INITIAL_ID_PHOTO'], jpg)
                id_face_photo = face_recognition.load_image_file(jpg.name)
            id_face_photo_encoding_list = face_recognition.face_encodings(id_face_photo)
            if len(id_face_photo_encoding_list) > 1:
                return make_response(jsonify({'success':False,'error': 'More than one face found in id photo'}),400)                
            id_face_photo_encoding = id_face_photo_encoding_list[0]
        except:
            return make_response(jsonify({'success':False,'error': 'No face found in id photo'}),400)            
        dist = numpy.linalg.norm(face_photo_encoding-id_face_photo_encoding)
        dist = 1-dist
        if dist>.50:
            print('validated')                
            # TODO: Create user model
                                    


            avg_model = (face_photo_encoding + id_face_photo_encoding) / 2
            b = avg_model.tolist()
            json_data =json.dumps(b)

            print(user["user_id"])
            m = hashlib.md5()	
            string_to_hash = str(user["user_id"]) + user["username"] 
            m.update(string_to_hash.encode())
            file_name = m.hexdigest()
            new_path = 'models/{}.json'.format(file_name)
            bucket = storage_client.get_bucket('jurisnovamx.appspot.com')
            blob = bucket.blob(new_path)
            blob.upload_from_string(json_data)
                    
            with __get_cursor() as cursor:
                
                sql = '''
                    INSERT INTO
                        users_facemodel (user_id, model)
                    VALUES (%(user_id)s,%(model_path)s)
                '''
                try:
                    cursor.execute(sql,{'user_id':id,'model_path':new_path})                         
                except Exception as e:
                    return make_response(jsonify({'success': True,'msg':'Validated but error at save model: {}'.format(e)}), 500)
                finally:
                    cursor.close()
            return make_response(jsonify({'success': True,'msg':'ID and photo match perfectly, model created'}), 200)
        else:
            return make_response(jsonify({'success': False,'msg':'Not match on faces'}), 200)
    return make_response(jsonify({'success': False,'msg':'No user found'}), 200)

@app.route('/validateModel/<id>')
def validateModel(id):
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

        #request_json = request.get_json(silent=True)
        #if request_json and 'user_id' in request_json:
        #    name = request_json['user_id']
        #else:
        #    raise ValueError("JSON is invalid, or missing a 'user_id' property")
        print(id)
        sql = '''SELECT 
            * 
        FROM `users_facemodel` u         
        WHERE             
            u.user_id = {};'''.format(id)        
        try:
            cursor.execute(sql)
            results = cursor.fetchone()        
        except Exception as e:
            return make_response(jsonify({'success': False,'msg':'{}'.format(e)}), 500)
        finally:
            cursor.close()
    if results is None:        
        return make_response(jsonify({'success': False,'msg':'No user found'}), 200)
    storage_client = storage.Client()
    bucket = storage_client.get_bucket('jurisnovamx.appspot.com')
    model_blob = bucket.blob(results['model'])
    model = json.loads(model_blob.download_as_string())
    model_data = numpy.array(model)

    models_blob = bucket.blob('models/all.json')
    models = json.loads(models_blob.download_as_string())

    match = False
    for m in models:
        existend_encoding = numpy.array(m['model'])
        dist = numpy.linalg.norm(existend_encoding-model_data)
        if dist < 0.5:
            match = True
            break
    if match is True:
        return make_response(jsonify({'success': False,'msg':'Match other user'}),200)        



    return make_response(jsonify({'success': True,'msg':'No match found'}), 200)

if __name__ == "__main__":
    app.run(debug=True,host='0.0.0.0',port=int(os.environ.get('PORT', 8080)))