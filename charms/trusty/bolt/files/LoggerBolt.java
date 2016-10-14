package tengu.storm;

import backtype.storm.topology.BasicOutputCollector;
import backtype.storm.topology.OutputFieldsDeclarer;
import backtype.storm.topology.base.BaseBasicBolt;
import backtype.storm.tuple.Fields;
import backtype.storm.tuple.Tuple;
import backtype.storm.tuple.Values;

/**
 *
 * @author sander
 */
public class LoggerBolt extends BaseBasicBolt {

    @Override
    public void declareOutputFields(OutputFieldsDeclarer ofd) {
        ofd.declare(new Fields("logword"));
    }

    @Override
    public void execute(Tuple tuple, BasicOutputCollector boc) {
        String word = tuple.getString(0);
        boc.emit(new Values(word));

    }

}
