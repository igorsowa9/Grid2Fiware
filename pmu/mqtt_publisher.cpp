#include "mqtt_publisher.h"
#include "utilities.h"

#include <string>
#include <cstring>
#include <ctime>
//#include <nlohmann/json.hpp>
//using nlohmann::json;


MQTTpublisher::MQTTpublisher()
{
}

MQTTpublisher::~MQTTpublisher()
{
    MQTTClient_disconnect(m_client, 10000);
    MQTTClient_destroy(&m_client);
}

bool MQTTpublisher::configure(ConfSection & conf)
{
    bool success = this->Publisher::configure(conf);
    if (!success) { return false; } 
    /**
     * get MQTT specific values
     **/

    success = getStringFromConf(conf, "PMU name", m_pmuname);
    if(!success) { return false; }

    success = getStringFromConf(conf, "broker", m_broker);
    if (!success) { return false; }

    success = getStringFromConf(conf, "topic", m_topic);
    if (!success) { return false; }

    success = getUIntFromConf(conf, "qos", m_qos);
    if (!success) { return false; }

    success = getStringFromConf(conf, "device", m_device);
    if (!success) { return false; }

    success = readStringVectorFromConf(conf, "meas_id", m_measIDs);
    if (!success) { return false; }

    success = readStringVectorFromConf(conf, "type", m_types);
    if (!success) { return false; }

    success = getStringFromConf(conf, "format", m_format);
    if (!success) { return false; }
    if (!isEqual(m_format, "ul") && !isEqual(m_format, "json")) {
        printf("MQTT format must be either \"ul\" or \"json\"!\n");
        return false;
    }

    int ret = createConnection();
    if (ret != 0) { return false; }

    return true;
}

int MQTTpublisher::createConnection()
{
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;

    int rc = MQTTClient_create(&m_client, m_broker.c_str(), m_pmuname.c_str(), MQTTCLIENT_PERSISTENCE_NONE, NULL);
    conn_opts.keepAliveInterval = 20;
    conn_opts.cleansession = 1;

    if ((rc = MQTTClient_connect(m_client, &conn_opts)) != MQTTCLIENT_SUCCESS)
    {
        printf("Failed to connect to MQTT broker %s\nreturn code: %d\n", m_broker.c_str(), rc);
    }

    return rc;
}

int MQTTpublisher::reconnect()
{
    MQTTClient_connectOptions conn_opts = MQTTClient_connectOptions_initializer;

    int rc;
    conn_opts.keepAliveInterval = 10;
    conn_opts.cleansession = 1;

    if ((rc = MQTTClient_connect(m_client, &conn_opts)) != MQTTCLIENT_SUCCESS)
    {
        printf("Failed to connect to MQTT broker %s\nreturn code: %d\n", m_broker.c_str(), rc);
    }

    return rc;
}
int MQTTpublisher::publish(publisher_data * data)
{
    phasor_data * samp = dynamic_cast<phasor_data*>(data);

    if (!samp)
    {
        std::cerr << "Sample processing function of IedModelNode was called with wrong type of sample data" << std::endl;
        return -1; 
    }

    std::vector<Phasor> phasors = (*samp).phasors; 
    return publish(phasors, samp->timestamp);
}

std::string msToISOdate(uint64_t timestamp_ms)
{
    time_t t_s  = static_cast<time_t>(timestamp_ms / 1000);
    char t_sss[30];
    strftime(t_sss, sizeof(t_sss), "%Y-%m-%dT%H:%M:%S", gmtime(&t_s));
    return t_sss;
}

std::string msToISOdate_ms(uint64_t timestamp_ms)
{
    unsigned int ms = timestamp_ms % 1000;
    time_t t_s  = static_cast<time_t>(timestamp_ms / 1000);
    char t_sss[30];
    size_t length = strftime(t_sss, sizeof(t_sss), "%Y-%m-%dT%H:%M:%S", gmtime(&t_s));
    sprintf(&t_sss[length], ":%u", ms);
    return t_sss;
}

int MQTTpublisher::send_msg(const std::string & payload, MQTTClient_message * msg, MQTTClient_deliveryToken * token)
{
    (*msg).payload = (void*) payload.c_str();
    (*msg).payloadlen = payload.length();
    MQTTClient_publishMessage(m_client, m_topic.c_str(), msg, token);
    int rc = MQTTClient_waitForCompletion(m_client, *token, 10000);
    if (0 != rc)
    {
        reconnect();
        send_msg(payload, msg, token);
//        printf("Message with delivery token %d could not be delivered, return code: %d\n", *token, rc);
    }
    return rc;
}

int MQTTpublisher::send_msg(char * payload, int payloadlen, MQTTClient_message * msg, MQTTClient_deliveryToken * token)
{
    (*msg).payload = (void*) payload;
    (*msg).payloadlen = payloadlen;
    MQTTClient_publishMessage(m_client, m_topic.c_str(), msg, token);
    int rc = MQTTClient_waitForCompletion(m_client, *token, 10000);
    if (0 != rc)
    {
        reconnect();
        send_msg(payload, payloadlen, msg, token);
//        printf("Message with delivery token %d could not be delivered, return code: %d\n", *token, rc);
    }
    return rc;
}

int MQTTpublisher::publish(const std::vector<Phasor>& phasors, uint64_t timestamp)
{
    std::string payload;
    std::vector<Phasor>::const_iterator phasIter;
    unsigned int channelNumber = 0;

    MQTTClient_message msg = MQTTClient_message_initializer;
    MQTTClient_deliveryToken token;
    msg.qos = m_qos;
    msg.retained = 0;
    int rc;
    char buf[1000];
    int buflen;
    double data;
    std::string type;

    // differentiate between Ultralight and JSON format
    if (isEqual(m_format, "json"))
    {
        for(phasIter = phasors.begin(); phasIter != phasors.end(); phasIter++)
        {
            type = m_types[channelNumber] + "_abs";
            data = (*phasIter).magFloat*pow(2, (*phasIter).magInt);
            buflen = sprintf(buf, "{\"device\":\"%s\",\"timestamp\":\"%s\",\"meas_id\":\"%s\",\"type\":\"%s\",\"data\":%f}", \
                            m_device.c_str(), msToISOdate_ms(timestamp).c_str(), m_measIDs[channelNumber].c_str(), type.c_str(), data);

            rc = send_msg(buf, buflen, &msg, &token);
            channelNumber++;
        }
        return rc;
    }
    else if (isEqual(m_format, "ul"))
    {
        std::string channel = "ch0";
        for (phasIter = phasors.begin(); phasIter != phasors.end(); phasIter++)
        {
            payload += phasorAsString(*phasIter, channel, timestamp);
            channelNumber++;
            channel = channel.replace(channel.size() -1, 1, std::to_string(channelNumber));
        } 

        msg.payload = (void*) payload.c_str();
        // cut off the last '|' character in the message so it can be interpreted by the receiver
        msg.payloadlen = payload.length() - 1;
        MQTTClient_publishMessage(m_client, m_topic.c_str(), &msg, &token);
        int rc = MQTTClient_waitForCompletion(m_client, token, 10000);
        if (0 != rc)
        {
            printf("Message with delivery token %d could not be delivered, return code: %d\n", token, rc);
        }
        return rc;
    }
    else
    {
        return -1;
    }
}
