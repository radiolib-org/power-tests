#include <signal.h>
#include <math.h>
#include <stdio.h>

#include <RadioLib.h>
#include "hal/RPi/PiHal.h"

#define RADIO_BOARD_RADIOHAT_REV_A
#include "RadioBoards.h"

#include "rf_powermon_client.h"
#include "dc_powermon_client.h"

// if there is an attenuator in the measurement setup,
// and the RF power meter has no offset configuration,
// use this to add the offset, otherwise set to 0
#define GAIN_OFFSET     (30)

// uncomment when using USB RF power meter dongle
#define RF_POWERMON_USB

const int ocp_max = 140;
const int pwr_min = -9;
const int pwr_max = 22;
const int paDutyCycle_min = 1;
const int paDutyCycle_max = 4;
const int hpMax_min = 0;
const int hpMax_max = 7;

PiHal* hal = new PiHal(0);
SX1262 radio = new RadioModuleHal(hal);

static void sighandler(int signal) {
  (void)signal;
  exit(EXIT_SUCCESS);
}

// make sure the radio is powered off on exit
static void exithandler(void) {
  fprintf(stdout, "\n");
  fflush(stdout);
  rf_powermon_exit();
  radio.standby();
}

int main(int argc, char** argv) {
  (void)argc;
  (void)argv;

  atexit(exithandler);
  signal(SIGINT, sighandler);

  // initialize the radio
  fprintf(stdout, "[Radio] Initializing ... ");
  int state = radio.begin();
  if (state == RADIOLIB_ERR_NONE) {
    fprintf(stdout, "success!\n");
  } else {
    fprintf(stdout, "failed, code %d\n", state);
    return(state);
  }

  // connect to the RF power meter
  #ifdef RF_POWERMON_USB
  state = rf_powermon_init_serial("/dev/ttyUSB0", 115200);
  #else
  // when connecting to the server, it has to be running already!
  state = rf_powermon_init_socket("localhost", 41122);
  #endif
  if (state != EXIT_SUCCESS) {
    fprintf(stdout, "Failed to initialize RF powermon client - is the server running?\n");
    exit(EXIT_FAILURE);
  }

  // connect to the DC power meter server - it must be running already!
  state = dc_powermon_init_socket("localhost", 41123);
  if (state != EXIT_SUCCESS) {
    fprintf(stdout, "Failed to initialize DC powermon client - is the server running?\n");
    exit(EXIT_FAILURE);
  }

  // log the IDs
  char buff[64];
  rf_powermon_id(buff);
  fprintf(stdout, "Connected to RF power monitor: %s\n", buff);
  dc_powermon_id(buff);
  fprintf(stdout, "Connected to DC power monitor: %s\n", buff);

  // set the overcurrent limit to the maximum value
  state = radio.setCurrentLimit(ocp_max);
  fprintf(stdout, "setCurrentLimit, code %d\n\n", state);

  // print the header
  fprintf(stdout, "Set [dBm],paDutyCycle,hpMax,Measured [dBm],Bus voltage[V],Voltage[mV],Current[mA],Power [mW],Efficiency [%%]\n"); 

  // iterate over all combinations of configured power, paDutyCycle and hpMax
  float rf_pwr, p_shunt, i_shunt, v_shunt, v_bus, err;
  double eff;
  float last_p_offset;
  for(int pwr = pwr_min; pwr <= pwr_max; pwr++) {
    for(int paDutyCycle = paDutyCycle_min; paDutyCycle <= paDutyCycle_max; paDutyCycle++) {
      for(int hpMax = hpMax_min; hpMax <= hpMax_max; hpMax++) {
        // set the configuration and start transmitting
        radio.setOutputPower(pwr, paDutyCycle, hpMax);
        radio.transmitDirect();
        
        // wait a bit for the output to stabilize
        hal->delay(1000);

        // read the RF power
        rf_powermon_read(&rf_pwr);
        rf_pwr += GAIN_OFFSET;

        // read the DC power
        dc_powermon_read_power(&p_shunt);
	      if(hpMax == hpMax_min) {
          // it seems that with hpMax == 0, there is never any RF output
          // we can use that to substract the DC power and get a more accurate
          // efficiency calculation
          last_p_offset = p_shunt;
        
        } else {
          // read everything
          dc_powermon_read_current(&i_shunt);
          dc_powermon_read_vshunt(&v_shunt);
          dc_powermon_read_vbus(&v_bus);

          // calculate efficiency of the radio
          eff = 100.0 * pow(10, (double)rf_pwr/10.0) / (double)(p_shunt - last_p_offset);

          // print it out
          fprintf(stdout, "%9d,%11d,%5d,%14.2f,%14.2f,%11.2f,%11.2f,%10.2f,%14.2f\n",
            pwr, paDutyCycle, hpMax, (double)rf_pwr, (double)v_bus,
            (double)v_shunt, (double)i_shunt, (double)p_shunt, eff);
          fflush(stdout);
        
        }
        
        // turn off the output and wait a bit to stabilize
        radio.standby();
        hal->delay(500);
      }
    
    }

  }

  return(EXIT_SUCCESS);
}
