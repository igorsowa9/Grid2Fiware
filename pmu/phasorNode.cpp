#include "phasorNode.h"
#include "utilities.h"
#include "phasor_publisher.h"

PhasorNode::PhasorNode(MMSServer * server) : Node(server)
{
    m_type = NodeType::PHASOR;
}

PhasorNode::~PhasorNode()
{
    free(twfactor1);                                                                              // FREE TWIDDLEFACTOR!!!!!
    free(twfactor2);
    free(twfactor3);
    free(twfactor4);
    free(twfactor5);
    free(m_window_chan0);                                                                   
    free(m_window_chan1);
    free(m_window_chan2);
    free(m_window_chan3);
    free(m_window_chan4);
    free(m_window_chan5);
}

bool PhasorNode::configure(ConfSection & conf)
{
    /**
     *  values for phasor calculation
     **/
    int success = readUIntVectorFromConf(conf, "signalId", m_signalId);
    if (!success) { return false; } 

    // test whether m_signalId[0] gets overwritten by nspc here already
    //m_nspc = 40;

    success =  readUIntVectorFromConf(conf, "signalMap", m_signalMap);
    if (!success) { return false; }

    success = readDoubleVectorFromConf(conf, "ratio", m_ratio);
    if (!success) { return false; }


    /**
     *  get the source for this node
     **/
    std::string sourceName;
    success = getStringFromConf(conf, "source", sourceName);
    if (!success) { return false; }

    Source * source = Source::source_by_name(sourceName);
    if (!source)
    {
        std::cerr << "failed to configure PhasorNode: no source with name '" << sourceName << "' found" << std::endl;
        return false;
    }
    success = source->addNode(this);
    if (!success) { return false; }

    std::string allPublisherNames;
    success = getStringFromConf(conf, "publishers", allPublisherNames);
    if (success) 
    { 
        splitStringIntoTokens(allPublisherNames, ",", m_publisherNames); //split string and write into vector
    }

    return true;
}

void PhasorNode::prepare(Prepdata * data)
{
    setChannels(data->channels);
    setGainTable(data->gainTable);
    setFrequency(data->frequency);
    setNspc(data->nspc);
    setNumberOfScans(data->numberScans);
    
    setNumberOfPeriods(data->numberOfPeriods);
    setSlide(data->slide);
    setNspp(data->nspp);
    setWindowSize(data->windowsize);
    
    if ((m_numberOfPeriods/m_slide) != std::round(m_numberOfPeriods/m_slide))
    {
        std::cerr << "Number of Periods to be considered divided by the number of periods to slide is not an integer"<< std::endl;
    }
    
     // std::cerr << m_numberOfPeriods << "\n" << m_slide<< "\n" <<(m_numberOfPeriods/m_slide) << "\n"<< std::endl;

    calculateTwiddleFactor();
    createWindow(data->channels);
    cycleCounter = 0;
    mod_cycle = 0;
    createPhasors(data->channels);

    // get Publishers: this should happen once and after the configure function execution, because Publisher can be configured
    // after the PhasorNode in the configuration file
    for (std::vector<std::string>::iterator it = m_publisherNames.begin(); it != m_publisherNames.end(); it++)
    {
        m_publishers.push_back(Publisher::publisher_by_name(*it));
    }
}

void PhasorNode::calculateTwiddleFactor()   
{
    twfactor1 =(std::complex<double>*) malloc(m_windowsize * (sizeof(std::complex<double>)));                                         
    twfactor2 =(std::complex<double>*) malloc(m_windowsize * (sizeof(std::complex<double>)));
    twfactor3 =(std::complex<double>*) malloc(m_windowsize * (sizeof(std::complex<double>)));
    twfactor4 =(std::complex<double>*) malloc(m_windowsize * (sizeof(std::complex<double>)));
    twfactor5 =(std::complex<double>*) malloc(m_windowsize * (sizeof(std::complex<double>)));
    
    int k =  std::round(50*m_windowsize /m_frequency); // system frequency = 50Hz alternative k = numberOfPeriods
     std::complex<double> ki(k,0.0);
     std::complex<double> i(0.0, 1.0); 
     std::complex<double> mi_windowsize(m_windowsize, 0.0);                                             //CHECK HOW TO FIX THIS!!

	for (unsigned int m = 0; m < m_windowsize ; m++)
	{
	    std::complex<double> mi(m, 0.0);                                                             //CHECK HOW TO FIX THIS!!

		twfactor1[m]= std::exp(-2.0 * i * M_PI * (ki-2.0) * mi /mi_windowsize);
		twfactor2[m]= std::exp(-2.0 * i * M_PI * (ki-1.0) * mi /mi_windowsize);
		twfactor3[m]= std::exp(-2.0 * i * M_PI * (  ki  ) * mi /mi_windowsize);
		twfactor4[m]= std::exp(-2.0 * i * M_PI * (ki+1.0) * mi /mi_windowsize);
		twfactor5[m]= std::exp(-2.0 * i * M_PI * (ki+2.0) * mi /mi_windowsize);
    }

}

bool PhasorNode::processData(sample_t * sample)
{
    sample_mcc * samp = dynamic_cast<sample_mcc*>(sample);

    if (!samp)
    {
        std::cerr << "Sample processing function of PhasorNode was called with wrong type of sample data" << std::endl;
        return false;
    }

        std::vector<Phasor> phasors = calculatePhasors(samp);

    // publish data
    phasor_data data;
    data.phasors = phasors;
    data.timestamp = samp->timestamp;              // Rescale to window


    for (auto publisher : m_publishers)
    {
        publisher->publish(&data);
    }
    return true;
}

std::vector<Phasor> PhasorNode::calculatePhasors(sample_mcc * sample)
{
    std::cerr << "TIME START - " << msToISOdate_ms(sample->timestamp)<<std::endl;
    
    
    unsigned int numberOfChannels = m_channels.size();
    std::set<unsigned int>::iterator chanIter = m_channels.begin();
    unsigned int currentChannel = *chanIter;

    std::vector<float> datavolt(m_numberOfScans);
    std::complex<double> cPhasor[numberOfChannels];
    std::vector<float> Vmean(numberOfChannels);
    unsigned int CountCycles;
    std::vector<float> frequencyROC(numberOfChannels);    
    std::vector<float> ROCOF(numberOfChannels);

   Phasor phasor;

    unsigned int Np = getFrequency() / getNspc();
    std::vector<float> TPeriods(2*Np);//I initialize it with a big size because we could have higher frequencies than expected
    
    std::vector<float> window(m_windowsize);
     for (unsigned int chan = 0; chan < numberOfChannels; chan++ )
    {
       switch (chan) // Assign window of channel as working window
       {
          case (0):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan0[l];}break;
          case (1):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan1[l];}break;
          case (2):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan2[l];}break;
          case (3):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan3[l];}break;
          case (4):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan4[l];}break;
          case (5):
            for (unsigned int l = 0; l<m_windowsize; l++){window[l] = m_window_chan5[l];}break;
       }
       
    //  std::cerr << "Started calculation for Channel: " << chan <<std::endl;

        calculateVoltages(chan, currentChannel, (sample->dataIn), datavolt);
        setDatavolt(datavolt,49.85,10,0); //    setDatavolt(datavolt, desired_frequency, amplitude, phase) 
   //     printSamples(datavolt,1);
        calculatePhasorForChannel(chan, datavolt, window, TPeriods, CountCycles, cPhasor[chan], Vmean[chan], phasor); 
   //     calculateROCOFandShiftPhasor(ROCOF[chan], prevfreq, phasor);
        
        slideWindowForChannel(chan,datavolt);
     //   std::cerr << "Calculation for Channel has ended" <<std::endl;
     //   std::cerr << " " <<std::endl;

        chanIter++;
        if (m_channels.end() == chanIter) { chanIter = m_channels.begin(); }
        currentChannel = *chanIter;
    }

    //here we combine the previous calculation of the channels to get the signals
    unsigned int numberOfSignals = getSignalId().size();
    std::vector<Phasor> phasors(numberOfSignals);

 //   unsigned int N = 0;
    for (unsigned int signalCounter=0; signalCounter < numberOfSignals; signalCounter++)
    {
 //       phasors[signalCounter] = combinePhasorWithSignal(N, signalCounter, frequencyROC, ROCOF, cPhasor);
    }
    
    
    cycleCounter++;
    mod_cycle = cycleCounter % m_numberOfPeriods;
    
    std::cerr << "TIME END - " << msToISOdate_ms(sample->timestamp)<<std::endl;
    std::cerr << "  " << std::endl;
    return phasors;

}

void PhasorNode::calculateVoltages(unsigned int& channelCounter, unsigned int& actualChannel, uint16_t * dataIn, std::vector<float> & dataVolt)
{
    unsigned int numberOfChannels = m_channels.size();
    uint16_t dataSamples [m_numberOfScans];    
    unsigned int sample;

    for(unsigned int j = 0; j < m_numberOfScans; j++)
    {
        sample = j * numberOfChannels + channelCounter;
        dataSamples[j] = rint( dataIn[sample] * m_gainTable.getValue(actualChannel, 0) + m_gainTable.getValue(actualChannel, 1) );
        dataVolt[j] = volts_USB20X(dataSamples[j]);
   //     std::cerr << dataVolt[j] <<std::endl; 
    }
}

void PhasorNode::calculatePhasorForChannel(const unsigned int& chan, std::vector<float> & datavolt, std::vector<float> & window, std::vector<float> & TPeriods, unsigned int & CountCycles, std::complex<double> & cPhasor, float & Vmean, Phasor & phasor)
{
    std::complex<double> i(0.0, 1.0);
    CountCycles = 0;
    std::vector<float> filtervolt(m_numberOfScans+3);
    double modFT = 0.0;
    std::complex<double> Xo[5];
    std::complex<double> mi_windowsize(m_windowsize, 0.0);

    switch (chan) 
              {
                case 0:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan0[j];} break;
               case 1:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan1[j];} break;
                case 2:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan2[j];} break;
               case 3:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan3[j];} break;;
                case 4:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan4[j];} break;
               case 5:
                 for (unsigned int j = 0; j<5 ; j++) {Xo[j] = Xo_chan5[j];} break;
                }

    if (cycleCounter == 0)
    {
        for (unsigned int j = 0; j < 5; j++)
        {
           Xo[j] = std::complex<double>(0.0, 0.0);
        }
    //    std::cerr << "Phasor calculation initiated" << std::endl;
    }
    else if (cycleCounter < (m_numberOfPeriods/m_slide)-1)
    {
    //      std::cerr << "Window not full" << std::endl;
    }
    else if (cycleCounter == (m_numberOfPeriods/m_slide)-1)
    {

        std::complex<double> Xk[3];
        Phasor phasor;

        for (unsigned int j = 0; j<m_windowsize-m_numberOfScans; j++) //Alternative "-(m_nspp*m_slide)" Calculate all but the last slide
        {
            std::complex<double> measurement(window[j], 0.0);
            Xo[0] = Xo[0] + (sqrt(2)/ mi_windowsize) * twfactor1[j] * measurement; //(1.2)
            Xo[1] = Xo[1] + (sqrt(2)/ mi_windowsize) * twfactor2[j] * measurement;
            Xo[2] = Xo[2] + (sqrt(2)/ mi_windowsize) * twfactor3[j] * measurement;
            Xo[3] = Xo[3] + (sqrt(2)/ mi_windowsize) * twfactor4[j] * measurement;
            Xo[4] = Xo[4] + (sqrt(2)/ mi_windowsize) * twfactor5[j] * measurement;
        }

        for (unsigned int j = 0; j < m_numberOfScans; j++) // Alternative "(m_nspp*m_slide)" Last slide is in datavolt from calculateVoltages
        {
            std::complex<double> ivolt(datavolt[j], 0.0);          
            Xo[0] = Xo[0] + (sqrt(2)/ mi_windowsize) * twfactor1[m_windowsize-m_numberOfScans+j] * ivolt;
            Xo[1] = Xo[1] + (sqrt(2)/ mi_windowsize) * twfactor2[m_windowsize-m_numberOfScans+j] * ivolt;
            Xo[2] = Xo[2] + (sqrt(2)/ mi_windowsize) * twfactor3[m_windowsize-m_numberOfScans+j] * ivolt;
            Xo[3] = Xo[3] + (sqrt(2)/ mi_windowsize) * twfactor4[m_windowsize-m_numberOfScans+j] * ivolt;
            Xo[4] = Xo[4] + (sqrt(2)/ mi_windowsize) * twfactor5[m_windowsize-m_numberOfScans+j] * ivolt;
        }
       
        Xk[0] = -0.25 * Xo[0] + 0.5 * Xo[1] - 0.25 * Xo[2];
        Xk[1] = -0.25 * Xo[1] + 0.5 * Xo[2] - 0.25 * Xo[3];
        Xk[2] = -0.25 * Xo[2] + 0.5 * Xo[3] - 0.25 * Xo[4];

        phasor = enhancedInterpolation(Xk);
     //   std::cerr <<"======First Phasor calculated====== Magnitude: "<< phasor.magFloat<<" Phase: "<< phasor.phFloat *(180/M_PI) <<std::endl;
    }
    else
    {
        std::complex<double> Xk[3];
        std::complex<double> Xko[5];
        Phasor phasor;
        
        for (unsigned int j = 0; j<m_numberOfScans; j++)
        {
            std::complex<double> newmeasurement(datavolt[j], 0.0);
            std::complex<double> oldmeasurement(window[j+(m_numberOfScans*mod_cycle)], 0.0);
            Xo[0] = Xo[0] + (sqrt(2)/ mi_windowsize) * twfactor1[j+(m_numberOfScans*mod_cycle)] * (newmeasurement - oldmeasurement);  //(1.5)
            Xo[1] = Xo[1] + (sqrt(2)/ mi_windowsize) * twfactor2[j+(m_numberOfScans*mod_cycle)] * (newmeasurement - oldmeasurement);
            Xo[2] = Xo[2] + (sqrt(2)/ mi_windowsize) * twfactor3[j+(m_numberOfScans*mod_cycle)] * (newmeasurement - oldmeasurement);
            Xo[3] = Xo[3] + (sqrt(2)/ mi_windowsize) * twfactor4[j+(m_numberOfScans*mod_cycle)] * (newmeasurement - oldmeasurement);
            Xo[4] = Xo[4] + (sqrt(2)/ mi_windowsize) * twfactor5[j+(m_numberOfScans*mod_cycle)] * (newmeasurement - oldmeasurement);
        }
       

        Xko[0] = Xo[0] * std::conj( twfactor1[(m_numberOfScans*(mod_cycle+1)) % m_windowsize] );  //(1.6)
        Xko[1] = Xo[1] * std::conj( twfactor2[(m_numberOfScans*(mod_cycle+1)) % m_windowsize] );
        Xko[2] = Xo[2] * std::conj( twfactor3[(m_numberOfScans*(mod_cycle+1)) % m_windowsize] );
        Xko[3] = Xo[3] * std::conj( twfactor4[(m_numberOfScans*(mod_cycle+1)) % m_windowsize] );
        Xko[4] = Xo[4] * std::conj( twfactor5[(m_numberOfScans*(mod_cycle+1)) % m_windowsize] );
        
        Xk[0] = -0.25 * Xko[0] + 0.5 * Xko[1] - 0.25 * Xko[2]; //(1.7)
        Xk[1] = -0.25 * Xko[1] + 0.5 * Xko[2] - 0.25 * Xko[3]; 
        Xk[2] = -0.25 * Xko[2] + 0.5 * Xko[3] - 0.25 * Xko[4];
        phasor = enhancedInterpolation(Xk);
        printResults(phasor);

    
    }
    
    switch (chan) 
              {
                case 0:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan0[j] = Xo[j];} break;
               case 1:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan1[j] = Xo[j];} break;
                case 2:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan2[j] = Xo[j];} break;
               case 3:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan3[j] = Xo[j];} break;;
                case 4:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan4[j] = Xo[j];} break;
               case 5:
                 for (unsigned int j = 0; j<5 ; j++) {Xo_chan5[j] = Xo[j];} break;
                }
                
    cPhasor = pow(modFT,-1)* cPhasor;
}

void PhasorNode::setDatavolt(std::vector<float> & datavolt, const float & desired_f, const float & amplitude, const float & phase)
{
    double set_f = desired_f/5000.;
    for (unsigned int j = (cycleCounter*m_numberOfScans) ; j <  (m_numberOfScans+ cycleCounter*m_numberOfScans); j++)
    {
        datavolt[j-(cycleCounter*m_numberOfScans)] = amplitude * cos( (2* M_PI * set_f * j) + ((phase*M_PI)/180) );
    }
 //   for (unsigned int j = 0 ; j <  m_numberOfScans ; j++)
 //   {
 //       std::cerr << datavolt[j] <<std::endl; 
 //   }
}

void PhasorNode::printSamples (std::vector<float> & datavolt, const unsigned int & spacing)
{
    for(unsigned int j = 0; j < spacing; j++)
    {
        std::cerr << " " <<std::endl; 
    }
    
    for(unsigned int j = 0; j < m_numberOfScans; j++)
    {
            std::cerr << datavolt[j] <<std::endl; 
    }
    for(unsigned int j = 0; j < spacing; j++)
    {
        std::cerr << " " <<std::endl; 
    }
}

void PhasorNode::printResults (Phasor & phasor)
{
        std::cerr <<"======     Phasor updated    ====== " <<std::endl;
        std::cerr <<"  Magnitude: "<< phasor.magFloat <<" Phase: "<< phasor.phFloat *(180/M_PI) <<std::endl;
        std::cerr <<"  Frequency: "<< phasor.freqFloat << "  " << (mod_cycle+1) << ". part of Window updated" <<std::endl;
}

std::string PhasorNode::msToISOdate_ms(uint64_t timestamp_ms)
{
    unsigned int ms = timestamp_ms % 1000;
    time_t t_s  = static_cast<time_t>(timestamp_ms / 1000);
    char t_sss[30];
    size_t length = strftime(t_sss, sizeof(t_sss), "D: %Y-%m-%d T: %H:%M:%S", gmtime(&t_s));
    sprintf(&t_sss[length], ":%u", ms);
    return t_sss;
}

void PhasorNode::calculateROCOFandShiftPhasor(float & ROCOF, float*  prevfreq, Phasor & phasor)
{
    float prfr = *prevfreq;
    
    ROCOF = (phasor.freqFloat - prfr)*50;
 
        std::cerr <<"  prevfreq: "<< prfr <<std::endl;   
        std::cerr <<"  ROCOF: "<< ROCOF <<std::endl;
        std::cerr <<"  newfreq: "<< phasor.freqFloat <<std::endl;
        
    prevfreq = &phasor.freqFloat;
}

void PhasorNode::slideWindowForChannel(const unsigned int & chan, const std::vector<float> & datavolt)
{
       switch (chan) 
       {
          case 0:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan0[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
          case 1:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan1[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
          case 2:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan2[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
          case 3:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan3[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
          case 4:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan4[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
          case 5:
            for (unsigned int l = 0; l<m_numberOfScans; l++){m_window_chan5[l+(m_numberOfScans*mod_cycle)] = datavolt[l];}break;
        default:
            std::cerr << "Entered default during slide" <<std::endl;
            break; 
        }

    //   std::cerr <<"  "<< (mod_cycle+1) << ".part of Window updated from a total of " << m_numberOfPeriods << " parts" <<std::endl;
}

Phasor PhasorNode::combinePhasorWithSignal(unsigned int & N, const unsigned int & signalCounter, const std::vector<float> & frequencyROC, const std::vector<float> & ROCOF, std::complex<double> * cPhasor)
{
    std::complex<double> phasorOut;     
    double frequencyOut = 0.0;
    double rocofOut = 0.0;

    switch (m_signalId[signalCounter])
    {
        case (0): // in this case there is an independent signal
            //phasorOut = m_ratio[signalCounter] * cPhasor;
            phasorOut = m_ratio[signalCounter] * cPhasor[m_signalMap[N]];
            frequencyOut = frequencyROC[m_signalMap[N]];
            rocofOut = ROCOF[m_signalMap[N]];
            N += 1;
            break;
        case (1): // in this case there are two channels representing phase and neutral
            //phasorOut = m_ratio[signalCounter] * cPhasor;
            phasorOut = m_ratio[signalCounter] *( cPhasor[m_signalMap[N]] - cPhasor[m_signalMap[N+1]]);
            frequencyOut = frequencyROC[m_signalMap[N]];
            rocofOut = ROCOF[m_signalMap[N]];
            N += 2;
            break;

        case (2): //in this case there are three phase channels and the output is the positive sequence
            std::cout << "this case is not defined (signalId == 2)" << std::endl;
            break;

        default:
            std::cout << "phasor calc: type of signal not recognized, rewire cables and check the configuration fie, " <<signalCounter<<","<<m_signalId[signalCounter]<< std::endl;
            break;
    }

    double absOut = abs(phasorOut);
    double phOut = arg(phasorOut);

    //    while (phOut <= 0) {
    //        phOut = phOut + 2.0 * M_PI;
    //    }

    //std::cout << "absOut=" << absOut << ", phOut=" << phOut << ", frequencyOut=" << frequencyOut << ", rocofOut=" << rocofOut << std::endl;
    //std::cout <<std::endl;		
    // we store absolute value and then ph angle and frequency
    Phasor phasor;
    int exp1 = 0;
    float tempFloat = frexp(absOut, &exp1);
    phasor.magFloat = tempFloat;
    phasor.magInt = exp1;

    tempFloat = frexp(phOut, &exp1);
    phasor.phFloat = tempFloat;
    phasor.phInt = exp1;

    tempFloat = frexp(frequencyOut, &exp1);
    phasor.freqFloat = tempFloat;
    phasor.freqInt = exp1;

    tempFloat = frexp(rocofOut, &exp1);
    phasor.rocofFloat = tempFloat;
    phasor.rocofInt = exp1;

    return phasor;
}

double PhasorNode::volts_USB20X(uint16_t value)
{
    double volt = 0.0;
    volt = (value - 2048.)*10./2048.;
    return volt;
}

const std::vector<unsigned int> & PhasorNode::getSignalId() const
{
    return m_signalId;
}

const std::vector<unsigned int> & PhasorNode::getSignalMap() const
{
    return m_signalMap;
}

const std::vector<double> & PhasorNode::getRatio() const
{
    return m_ratio;
}

void PhasorNode::setChannels(const std::set<unsigned int>& channels)
{
    m_channels = channels;
    m_numberOfChannels = m_channels.size();
}

const std::set<unsigned int> & PhasorNode::getChannels() const
{
    return m_channels;
}

void PhasorNode::setGainTable(const GainTable & gainTable)
{
    m_gainTable = gainTable;
}

const GainTable & PhasorNode::getGainTable() const
{
    return m_gainTable;
}

void PhasorNode::setNumberOfScans(const unsigned int & numberScans)
{
    m_numberOfScans = numberScans;
}

const unsigned int & PhasorNode::getNumberOfScans() const
{
    return m_numberOfScans;
}

void PhasorNode::setFrequency(const unsigned int & frequency)
{
    m_frequency = frequency;
}

const unsigned int & PhasorNode::getFrequency() const
{
    return m_frequency;
}

void PhasorNode::setNspc(const unsigned int & numbersPerCycle)
{
    m_nspc = numbersPerCycle;
}

const unsigned int & PhasorNode::getNspc() const
{
    return m_nspc;
}

void PhasorNode::setNumberOfPeriods(const unsigned int & numberOfPeriods)
{
    m_numberOfPeriods = numberOfPeriods;
}

const unsigned int & PhasorNode::getNumberOfPeriods() const
{
    return m_numberOfPeriods;
}

void PhasorNode::setNspp(const unsigned int & numbersPerCycle)
{
    m_nspp = numbersPerCycle;
}

const unsigned int & PhasorNode::getNspp() const
{
    return m_nspp;
}

void PhasorNode::setSlide(const float & slide)
{
    m_slide = slide;
}

const float & PhasorNode::getSlide() const
{
    return m_slide;
}

void PhasorNode::setWindowSize(const unsigned int & windowsize)
{
    m_windowsize = m_nspp*m_numberOfPeriods;
}

void PhasorNode::createWindow(const std::set<unsigned int>& channels)
{
    m_channels = channels;
    unsigned int numberOfChannels = m_channels.size();

  prevfreq =(float*) malloc(sizeof(float));
switch (numberOfChannels) 
  {
  case (1):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float)));
//    std::cout << "1 windows created"<< std::endl; 
    break;
  case (2):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan1 =(float*) malloc(m_windowsize * (sizeof(float))); 
//    std::cout << "2 windows created"<< std::endl;
    break;
 case (3):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float)));
    m_window_chan1 =(float*) malloc(m_windowsize * (sizeof(float)));
    m_window_chan2 =(float*) malloc(m_windowsize * (sizeof(float)));
//    std::cout << "3 windows created"<< std::endl;
    break;
 case (4):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan1 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan2 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan3 =(float*) malloc(m_windowsize * (sizeof(float))); 
//    std::cout << "4 windows created"<< std::endl;
    break;
 case (5):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan1 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan2 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan3 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan4 =(float*) malloc(m_windowsize * (sizeof(float))); 
//    std::cout << "5 windows created"<< std::endl;
    break;
 case (6):
    m_window_chan0 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan1 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan2 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan3 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan4 =(float*) malloc(m_windowsize * (sizeof(float))); 
    m_window_chan5 =(float*) malloc(m_windowsize * (sizeof(float))); 
//   std::cout << "6 windows created"<< std::endl;
    break;    
  default:
    std::cout << "Switch case for m_window did not work"<< std::endl;
    break;
  } 
}
void PhasorNode::createPhasors(const std::set<unsigned int>& channels)
{
    m_channels = channels;
    unsigned int numberOfChannels = m_channels.size();

switch (numberOfChannels) 
  {
  case (1):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
//    std::cout << "1 windows created"<< std::endl; 
    break;
  case (2):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan1 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
//    std::cout << "2 windows created"<< std::endl;
    break;
 case (3):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan1 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan2 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    //    std::cout << "3 windows created"<< std::endl;
    break;
 case (4):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan1 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan2 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan3 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
//    std::cout << "4 windows created"<< std::endl;
    break;
 case (5):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan1 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan2 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan3 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan4 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
//    std::cout << "5 windows created"<< std::endl;
    break;
 case (6):
    Xo_chan0 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan1 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan2 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan3 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>))); 
    Xo_chan4 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    Xo_chan5 =(std::complex<double>*) malloc(5 * (sizeof(std::complex<double>)));
    
//   std::cout << "6 windows created"<< std::endl;
    break;    
  default:
    std::cout << "Switch case for m_window did not work"<< std::endl;
    break;
  } 
}

Phasor PhasorNode::enhancedInterpolation(const std::complex<double> Xk[3])
{
    Phasor phasor;
    int y = 0;
    double yhelp = std::abs(Xk[0]) - std::abs(Xk[2]);    //build ypslon
    
    if (yhelp == 0) { y = 0;} 
    else if (yhelp < 0) { y = -1;}
    else { y = 1;} 
    
    double alpha = std::abs( Xk[1] / Xk[1+y] ); //(2.6)
    double delta_bin = y * ((2-alpha)/(1+alpha));
    
    double mag = 2 * std::abs(Xk[1]) * (M_PI * delta_bin * (1 - pow(delta_bin,2))) / sin(M_PI*delta_bin); //(2.7)
    double ang = std::arg(Xk[1]) - M_PI*delta_bin;  //(2.8)
    
    std::complex<double> i(0.0, 1.0);
    std::complex<double> VI = (mag/(2.0 * i)) * std::exp(i * ang); // Build VI (under 2.9)
    
  //  int k =  std::round(50*m_windowsize /m_frequency); // system frequency = 50Hz alternative k = numberOfPeriods
    double kd =  std::round(50*m_windowsize /m_frequency); // system frequency = 50Hz alternative k = numberOfPeriods
    std::complex<double> mi_windowsize(m_windowsize, 0.0);
   
    std::complex<double> gamma = std::conj(VI) * (WR(2*kd+delta_bin,m_windowsize)/mi_windowsize); //(2.14)
    std::complex<double> omega = std::conj(VI) * (WR(2*kd+y+delta_bin,m_windowsize)/mi_windowsize); //(2.15)
    
    alpha = std::abs( Xk[1] - gamma)/ std::abs( Xk[1+y] - omega) ; //(2.16)
    delta_bin = (y * (2-alpha))/(1+alpha); //(2.6) 
    
    mag = 2 * std::abs(Xk[1]) * (M_PI * delta_bin * (1 - pow(delta_bin,2))) / sin(M_PI*delta_bin); //(2.7)
    ang = std::arg(Xk[1]) - M_PI*delta_bin;    //(2.8)

    phasor.magFloat = mag;
    phasor.phFloat = ang;
    phasor.freqFloat = 50  + delta_bin  * (m_frequency / m_windowsize) ;

//    std::cout << "Delta bin: "<< delta_bin << std::endl;
//    std::cout << "K:         "<< k << std::endl;
    return phasor;
}

std::complex<double> PhasorNode::WR(double k, double N)
{
    std::complex<double> ki(k,0.0);
    std::complex<double> i(0.0, 1.0); 
    std::complex<double> Ni(N, 0.0);  
    
    std::complex<double> W_R = std::exp(-1.0 * i * M_PI * ki *(Ni-1.)/Ni) * (sin(M_PI*k))/(sin(M_PI*k/N));
    std::cout << "Wr: "<< W_R << std::endl;
    
    return W_R;
}

void PhasorNode::printPhasor(const Phasor& phasor)
{
    std::cout << "Phasor: magInt=" << phasor.magInt << ", magFloat=" << phasor.magFloat << ", phInt=" << phasor.phInt << ", phFloat=" << phasor.phFloat
        << ", freqInt=" << phasor.freqInt << ", freqFloat=" << phasor.freqFloat << ", rocofInt=" << phasor.rocofInt << ", rocofFloat=" << phasor.rocofFloat
        << std::endl;
}

	
