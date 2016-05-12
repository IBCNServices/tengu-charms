/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package tengu.storm;

import backtype.storm.topology.BasicOutputCollector;
import backtype.storm.topology.OutputFieldsDeclarer;
import backtype.storm.topology.base.BaseBasicBolt;
import backtype.storm.tuple.Fields;
import backtype.storm.tuple.Tuple;
import com.mongodb.MongoClient;
import com.mongodb.client.MongoDatabase;
import org.bson.Document;
import org.json.JSONException;
import org.json.JSONObject;

/**
 *
 * @author sander
 */
public class MongoBolt extends BaseBasicBolt{
    private transient MongoDatabase db;
    private String message;
    
    public void prepareConfig(String mongo_ip, String mongoPort, String dbName, String m){
	message = m;
        int mongo_port = Integer.parseInt(mongoPort.toString());
        System.out.format("Mongo_connect: %s:%d ", mongo_ip, mongo_port);
        MongoClient mongoClient = new MongoClient(mongo_ip, mongo_port);
        db = mongoClient.getDatabase(dbName);
        System.out.println("GOT_DATABASE");
    }

    @Override
    public void declareOutputFields(OutputFieldsDeclarer declarer) {
        declarer.declare(new Fields(""));
    }

    @Override
    public void execute(Tuple input, BasicOutputCollector collector) {
        System.out.println("DID_EXECUTE");
        JSONObject obj = new JSONObject(input.getStringByField(message));
        try {
            System.out.println("START_TRY");
            String collection = obj.getString("collectionId");
            JSONObject json = obj.getJSONObject(message);
            db.getCollection(collection).insertOne(Document.parse(json.toString()));
            System.out.println("END_TRY");
        } catch (JSONException ex) {
            System.out.println("START_EXC");
            String collection = "00000";
            db.getCollection(collection).insertOne(Document.parse(obj.toString()));
            System.out.println("END_EX");
        }
    }
}
