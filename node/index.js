const {Storage} = require('@google-cloud/storage');
const mysql = require('mysql');
const{ Facenet } = require('facenet');
const tempfile = require('tempfile');

const storage = new Storage();

const connectionName = process.env.INSTANCE_CONNECTION_NAME || 'localhost';
const dbUser = process.env.SQL_USER || 'root';
const dbPassword = process.env.SQL_PASSWORD || 'jurisnova@2019';
const dbName = process.env.SQL_NAME || 'jurisnova';

const mysqlConfig = {
    connectionLimit: 1,
    user: dbUser,
    password: dbPassword,
    database: dbName,
};

let mysqlPool;
/**
 * Responds to any HTTP request.
 *
 * @param {!express:Request} req HTTP request context.
 * @param {!express:Response} res HTTP response context.
 */
/*exports.helloWorld = (req, res) => {
    let message = req.query.message || req.body.message || 'Hello World!';
    res.status(200).send(message);
};*/
  


test = () => {
    if (process.env.NODE_ENV === 'production') {
        mysqlConfig.socketPath = `/cloudsql/${connectionName}`;
    }
    if (!mysqlPool) {
        mysqlPool = mysql.createPool(mysqlConfig);
    }
    /*let user_id = req.query.user_id || req.body.user_id || 0;
    if (user_id === 0) {        
        //res.status(400).json({error:.'No user_id in params'});
        return;        
    }*/
    let user_id = 7
    mysqlPool.query(`SELECT 
    u.photos_path, 
    u.user_id, 
    ui.file_name, 
    ui.image_type 
FROM users_info u 
JOIN users_image ui 
ON 
    ui.user_id=u.user_id 
WHERE 
    is_valid = 0
    AND  u.user_id = ${user_id} 
    AND ui.validated = 0;`, async (err, results) => {
        if (err) {
            console.error(err);
            //res.status(500).send(err);
        } else { 
            if (results.length !== 2 ) {
                console.log('inconsistence data');
                //res.status(500).json({error:'Data may be corrupted'});
                return;
            }

            let user_info = {
                photos_path: results[0].photos_path
            }
            user_info[results[0].image_type] = results[0].file_name;
            user_info[results[1].image_type] = results[1].file_name;
                     

            const options = {
                version: 'v2', // defaults to 'v2' if missing.
                action: 'read',
                expires: Date.now() + 1000 * 60, // 1 minute
            };              
            let url_photo;            
            try{
                url_photo = await storage.bucket('jurisnovamx.appspot.com').file(user_info.photos_path + user_info.INITIAL_PHOTO).getSignedUrl(options);
            } catch(e){
                console.log('error on loading data photo',e)
                //res.status(500).json({error:'Image file can not be loades'});  
                process.exit()              
                return;
            }
            let url_id_photo;
            try{
                url_id_photo = await storage.bucket('jurisnovamx.appspot.com').file(user_info.photos_path + user_info.INITIAL_ID_PHOTO).getSignedUrl(options);
            } catch(e){
                console.log('error on loading data id photo',e)                
                //res.status(500).json({error:'ID Image file can not be loades'});
                process.exit()
                return;
            }
            // Do Face Alignment, return faces  
            
            try {
                const facenet = new Facenet();          
                const faceList = await facenet.align(url_photo[0])
                console.log('face',faceList)
            } catch (error) {
                console.log('error on loading data id photo',error)                
                //res.status(500).json({error:'ID Image file can not be loades'});
                process.exit()
                return;
            }


            
            /*if(faceList.length > 1){
                console.log('More than one face in photo')
                return;
            }
            const face = faceList[0]
            console.log('bounding box:',  face.boundingBox)
            console.log('landmarks:',     face.facialLandmark)

            // Calculate Face Embedding, return feature vector
            const embedding = await facenet.embedding(face)
            console.log('embedding:', embedding)            */
            throw 'finish'
            //res.send(JSON.stringify(results));
        }
    });
    
}

test()