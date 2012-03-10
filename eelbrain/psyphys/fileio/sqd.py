'''
tools for MEG 160 .sqd files

Created on Jan 26, 2012

@author: christian
'''
import numpy as np
import struct
import sys
import os.path


class sqd_file(object):
    '''
    Class for reading MEG 160 .sqd files. 
    
    Based on cephalo's sqd2h5 (GNU license):
    http://pealco.net/cephalo/
    
    '''
    def __init__(self, filename):
        self.filename = filename
        self.file = open(filename, 'rb')
        
        self.get_basic_info()
        self.get_sensitivity_info()
        self.get_amplifier_info()
        self.get_acquisition_parameters()
        self.get_data_info()
        self.get_patient_info()
        self.compute_convfactor()
    
    def get_hdr(self):
        
    
    def get(self, ctype, size=1):
        """Reads and unpacks binary data into the desired ctype."""
        chunk = self.file.read(struct.calcsize(ctype) * size)
        return struct.unpack(ctype * size, chunk)
    
    def get_basic_info(self):
        self.file.seek(16)
        basic_offset = self.get('l')[0]

        self.file.seek(basic_offset)
        self.version       = self.get('i')[0]
        self.revision      = self.get('i')[0]
        self.system_id     = self.get('i')[0]
        self.system_name   = ", ".join(self.get('128s')[0].strip("\n\x00").split("\n"))
        self.model_name    = self.get('128s')[0].strip("\n\x00")
        self.channel_count = self.get('i')[0]
        self.comment       = self.get('s', 256)[0].rstrip("\n\x00")

    def get_patient_info(self):
        self.file.seek(32)
        patient_offset = self.get('l')[0]
        size           = self.get('l')[0]
        maxcount       = self.get('l')[0]
        count          = self.get('l')[0]

        current_offset = patient_offset
        while current_offset < (patient_offset + size * count):
            self.file.seek(current_offset)
            infosize = self.get('l')[0]
            code     = self.get('l')[0]
            subcode  = self.get('l')[0]
            data = self.get('c', infosize)
            dataend  = flatnonzero(array(data)=='')[0]
            data     = ''.join(data[0:dataend])
            if subcode == 1:
                if code == 1:
                    self.patient_id = data
                elif code == 2:
                    self.patient_name = data
                elif code == 3:
                    self.patient_birthdate = data
                elif code == 4:
                    self.patient_gender = data
                elif code == 5:
                    self.patient_handedness = data

            current_offset += infosize



    def get_sensitivity_info(self):
        # Get offset of sensitivity values
        self.file.seek(80)
        sensitivity_offset = self.get('l')[0]

        # Read sensitivity data
        self.file.seek(sensitivity_offset)
        self.sensitivity = list(self.get('d', self.channel_count * 2))
        self.sensitivity = zip(*[iter(self.sensitivity)]*2) # Gets elements from the list by 2

    def get_amplifier_info(self):
        # Get offset of amplifier information
        self.file.seek(112)
        amp_offset = self.get('l')[0]

        # Get amplifier data
        self.file.seek(amp_offset)
        self.amp_data = self.get('i')[0]

        InputGainBit = 11
        InputGainMask = 0x1800
        input_gain_index = (self.amp_data & InputGainMask) >> InputGainBit
        input_gain_multipliers = [1, 2, 5, 10]
        self.input_gain = input_gain_multipliers[input_gain_index]

        OutputGainBit = 0
        OutputGainMask = 0x0007
        output_gain_index = (self.amp_data & OutputGainMask) >> OutputGainBit
        output_gain_multipliers = [1, 2, 5, 10, 20, 50, 100, 200]
        self.output_gain = output_gain_multipliers[output_gain_index]

    def get_acquisition_parameters(self):
        # Get offset of acquisition parameters
        self.file.seek(128)
        acqcond_offset = self.get('l')[0]

        self.file.seek(acqcond_offset)
        self.acq_type = self.get('l')[0]

        if self.acq_type == 1:
            # Read acquisition parameters
            self.acq_type_desc = "Continuous mode, Raw data file"
            self.sample_rate = self.get('d')[0]
            self.sample_count = self.get('l')[0]
            self.actual_sample_count = self.get('l')[0]
            self.file.seek(144)
            self.raw_offset = self.get('l')[0]

        elif self.acq_type == 2:
            # Read acquisition parameters
            self.acq_type_desc = "Evoked mode, Average data file"
            self.sample_rate = self.get('d')[0]
            self.frame_length = self.get('l')[0]
            self.pretrigger_length = self.get('l')[0]
            self.average_count = self.get('l')[0]
            self.actual_average_count = self.get('l')[0]

        elif self.acq_type == 3:
            # Read acquisition parameters
            self.acq_type_desc = "Evoked mode, Raw data file"
            self.sample_rate = self.get('d')[0]
            self.frame_length = self.get('l')[0]
            self.pretrigger_length = self.get('l')[0]
            self.average_count = self.get('l')[0]
            self.actual_average_count = self.get('l')[0]

        else:
            print "Bad file!"


    def get_data_info(self):
        if self.acq_type == 1:
            self.file.seek(144)
            self.raw_offset = self.get('l')[0]
            self.data_type = 'h' # 2-byte Integer
        elif acq_type == 2:
            self.file.seek(160)
            self.ave_offset = self.get('l')[0]
            self.data_type = 'd' # 8-byte Real
        elif acq_type == 3:
            f.seek(144)
            raw_offset = self.get('l')[0]
            self.data_type = 'h' # 2-byte Integer
        else:
            print "Error!"


    def get_channel(self, channel):
        numbytes = 2 # FIXME
        chan_offset = channel
        sample_offset = self.channel_count
        self.file.seek(self.raw_offset + (chan_offset * numbytes))
        chunk = 'h' + str(numbytes * (self.channel_count - 1)) + 'x'
        divisor = int(self.sample_rate)
        
        data = np.zeros(self.actual_sample_count, dtype='int16')
        for block in xrange((self.actual_sample_count-1)/divisor):
            a = block * divisor
            b = a + divisor
            data[a:b] = list(self.get(chunk*divisor))
            
        data[b:] = list(self.get((chunk * (divisor - 1)) + 'h' + \
                                 str((self.channel_count - 1 - channel) * numbytes) + 'x'))
                
        #data = [list(self.get(chunk*divisor)) for _ in xrange((self.actual_sample_count-1)/divisor)]
        #data += [list(self.get((chunk * (divisor - 1)) + 'h' + str((192 - 1 - channel) * numbytes) + 'x'))]
        #data = array(data).flatten()
        
        return data
        
    
    def compute_convfactor(self):
        gain = array([y for x, y in self.sensitivity])
        ampgain = self.output_gain/float(self.input_gain)
        
        self.convfactor = ones(self.channel_count) * ampgain * (gain * 10**12) / (2**12)

    def __repr__(self):
        out = []
        out.append("Basic Information")
        out.append("\tMEG160 version: V%dR%03d" % (self.version, self.revision))
        out.append("\tSystem ID:      %d" % self.system_id)
        out.append("\tSystem Name:    %s" % self.system_name)
        out.append("\tModel:          %s" % self.model_name)
        out.append("\tChannel count:  %d" % self.channel_count)
        out.append("\tComment:        %s" % self.comment)
        out.append("Amplifier information")
        out.append("\tInput gain:      x%d" % self.input_gain)
        out.append("\tOutput gain:     x%d" % self.output_gain)
        out.append("Acquisition information")
        if self.acq_type == 1:
            out.append("\tContinuous mode, Raw data file")
            out.append("\tSampling Rate:       %lg Hz" % self.sample_rate)
            out.append("\tSample Count:        %ld samples" % self.sample_count)
            out.append("\tActual Sample Count: %ld samples" % self.actual_sample_count)
            out.append("\tData Offset:         %ld bytes" % self.raw_offset)
        elif self.acq_type == 2:
            out.append("\tEvoked mode, Average data file")
            out.append("\tSampling Rate:        %lg Hz" % self.sample_rate)
            out.append("\tFrame Length:         %ld samples" % self.frame_length)
            out.append("\tPretrigger Length:    %ld samples" % self.pretrigger_length)
            out.append("\tAverage Count:        %ld" % self.average_count)
            out.append("\tActual Average Count: %ld" % self.actual_average_count)
        elif self.acq_type == 3:
            out.append("\tEvoked mode, Raw data file")
            out.append("\tSampling Rate        = %lg[Hz]" % self.sample_rate)
            out.append("\tFrame Length         = %ld[sample]" % self.frame_length)
            out.append("\tPretrigger Length    = %ld[sample]" % self.pretrigger_length)
            out.append("\tAverage Count        = %ld" % self.average_count)
            out.append("\tActual Average Count = %ld" % self.actual_average_count)

        return "\n".join(out)

    def info(self):
        return self.__repr__()

def load(squid, h5f):
    for channel in xrange(squid.channel_count):
#        print "Reading channel %d ..." % channel
        h5f.root.raw_data[channel, :] = squid.get_channel(channel)


def main(sqd_filename):
    squid = SquidData(sqd_filename)

    h5_filename = os.path.splitext(sqd_filename)[0] + ".h5"
    array_shape = (squid.channel_count, squid.actual_sample_count)

    h5f = tables.openFile(h5_filename, mode='w', title="MEG data")

    h5f.createCArray(
        where=h5f.root, 
        name='raw_data', 
        atom=tables.Int16Atom(), 
        shape=array_shape,
        filters=tables.Filters(1))


    h5f.createCArray(
        where=h5f.root, 
        name='convfactor', 
        atom=tables.Float32Atom(), 
        shape=shape(squid.convfactor), 
        filters=tables.Filters(1))
    h5f.root.convfactor[:] = squid.convfactor

    load(squid, h5f)

    print "Output %s" % h5_filename
    h5f.close()
