/*
 * To change this license header, choose License Headers in Project Properties.
 * To change this template file, choose Tools | Templates
 * and open the template in the editor.
 */
package tengu.storm;

import backtype.storm.tuple.Fields;
import storm.kafka.StringKeyValueScheme;

/**
 *
 * @author sander
 */
public class KafkaBoltKeyValueScheme extends StringKeyValueScheme {
    private String fieldName;
    
    public KafkaBoltKeyValueScheme(){
    
    }
    
    public KafkaBoltKeyValueScheme(String fieldName){
        this.fieldName = fieldName;
    }
    
    @Override
    public Fields getOutputFields() {
        return new Fields(fieldName);
    }
}
