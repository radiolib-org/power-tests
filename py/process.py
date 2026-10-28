import csv
import os
from typing import List, Dict
from collections import Counter 

# set to true when processing LR2021 data
IS_LR2021 = True

# this is the maximum allow power difference between reference power output (from default PA table)
# and the optimized configuration
MAX_ALLOWED_POWER_DIFF = 0.2

KEY_MEASURED = "Measured [dBm]"
KEY_POWER = "Power [mW]"
KEY_PA_CONF_A = "paDutyCycle"

if IS_LR2021:
  KEY_SET = "Set [dBm/2]"
  KEY_PA_CONF_B = "paSlc"
else:
  KEY_SET = "Set [dBm]"
  KEY_PA_CONF_B = "hpMax"

# PA tables format is KEY_PA_CONF_A, KEY_PA_CONF_B, PWR_SET
if IS_LR2021:
  
  DEF_PA_TABLE = [
    # LR2021 default PA table is not defined below +10 dBm; the values here are based on what was actually measured
    [6, 7, -9], [6, 7, -8], [6, 7, -7], [6, 7, -6], [6, 7, -5], [7, 4, -4], [7, 4, -3], [7, 4, -2],
    [7, 4, -1], [7, 4, 0], [7, 7, 1], [7, 5, 4], [7, 5, 6], [7, 5, 8], [7, 5, 10], [7, 6, 12], 
    [7, 6, 14], [7, 4, 16], [6, 6, 19], 
    # actual default PA table from datasheet starts here
    [2, 1, 16], [2, 2, 16], [5, 1, 15], [4, 3, 15.5], [4, 2, 17], [5, 4, 16.5], [4, 4, 18], [5, 6, 18], 
    [5, 6, 19], [6, 6, 19.5], [6, 6, 20.5], [7, 7, 21], [7, 6, 22]
  ]
else:
  # for SX126x, the default PA table is just paDutyCycle = 4 and hpMax = 7
  DEF_PA_TABLE = [
    [4, 7, -9], [4, 7, -8], [4, 7, -7], [4, 7, -6], [4, 7, -5], [4, 7, -4], [4, 7, -3], [4, 7, -2], 
    [4, 7, -1], [4, 7, 0], [4, 7, 1], [4, 7, 2], [4, 7, 3], [4, 7, 4], [4, 7, 5], [4, 7, 6], 
    [4, 7, 7], [4, 7, 8], [4, 7, 9], [4, 7, 10], [4, 7, 11], [4, 7, 12], [4, 7, 13], [4, 7, 14], 
    [4, 7, 15], [4, 7, 16], [4, 7, 17], [4, 7, 18], [4, 7, 19], [4, 7, 20], [4, 7, 21], [4, 7, 22],
  ]

def get_unique_values(key: str, data: List[Dict[str, float]]) -> List[float]:
    unique_sets = sorted({row[key] for row in data})
    return unique_sets

def filter_by_key(key: str, value: float, data: List[Dict[str, float]]) -> List[Dict[str, float]]:
    return [row for row in data if row[key] == value]

def filter_by_range(key: str, value: float, tol_min: float, tol_max: float, data: List[Dict[str, float]]) -> List[Dict[str, float]]:
    return [row for row in data if ((row[key] >= (value + tol_min)) and (row[key] <= (value + tol_max)))]

def parse_rf_data(csv_file_path: str) -> List[Dict[str, float]]:
    data: List[Dict[str, float]] = []
    
    with open(csv_file_path, 'r', newline='', encoding='utf-8') as f:
        reader = csv.reader(f)
        # first 5 lines are the header, skip them
        for i in range(5):
          next(reader)
        
        # Read header row (already split into list by csv.reader)
        header_line = next(reader)
        headers = [h.strip() for h in header_line]  # Just strip, no .split()
        
        # Parse data rows
        for row in reader:
            row = [cell.strip() for cell in row]  # Strip whitespace from each cell
            if not row or all(cell == '' for cell in row):
                continue  # Skip empty rows
            if len(row) != len(headers):
                continue  # Skip malformed rows
            row_dict = dict(zip(headers, row))
            # convert everything to floats
            for k, v in row_dict.items():
                row_dict[k] = float(v)
            data.append(row_dict)
    
    return data


def main(log_dir_path: str):
    out = open("out/optimized.csv", "w+")
    out.write(f"Pout,{KEY_SET},{KEY_PA_CONF_A},{KEY_PA_CONF_B},{KEY_MEASURED},{KEY_POWER}\n")
    opt_settings: List[Dict[str, Any]] = []
    power_levels = []

    # iterate over all .log files in the provided directory
    directory = os.fsencode(log_dir_path)
    num_measurements = 0
    for file in os.listdir(directory):
        filename = os.fsdecode(file)
        if not filename.endswith(".log"):
            continue

        # Parse data
        data = parse_rf_data(log_dir_path + "/" + filename)
        if IS_LR2021:
          for d in data:
            d[KEY_SET] /= 2
        num_measurements += 1
        
        # get the configured power levels
        power_levels = get_unique_values(KEY_SET, data)

        for pwr in power_levels:
            if pwr - int(pwr) != 0:
              continue

            # find the actual measured value with the default PA configuration, this is the reference
            entries = filter_by_key(KEY_SET, pwr, data)
            idx = int(pwr) + 9
            key_a = DEF_PA_TABLE[idx][0]
            key_b = DEF_PA_TABLE[idx][1]
            entries = filter_by_key(KEY_PA_CONF_A, key_a, entries)
            entries = filter_by_key(KEY_PA_CONF_B, key_b, entries)
            ref_level = entries[0][KEY_MEASURED]
            ref_power = entries[0][KEY_POWER]
        
            # find settings that produce something close to this reference value and sort them by power consumption
            entries = filter_by_range(KEY_MEASURED, ref_level, 0, 0.2, data)
            entries.sort(key=lambda x: x[KEY_POWER])
            optimal = entries[0]
            optimal['target'] = pwr
            set_val = optimal[KEY_SET]
            if IS_LR2021:
              set_val *= 2
            optimal['paCfg'] = f"{set_val:.0f},{optimal[KEY_PA_CONF_A]:.0f},{optimal[KEY_PA_CONF_B]:.0f}"
            opt_settings.append(optimal)

            # the first one is the result
            saving = 100 * (ref_power - optimal[KEY_POWER]) / ref_power
            #print(f"Optimized {pwr:2.0f} dBm: actual={optimal[KEY_MEASURED]} (was {ref_level:.2f}) Power: {ref_power} -> {optimal[KEY_POWER]} (-{saving:.2f}%)")
            
            # dump it to file for further analysis
            out.write(f"{pwr:.1f},{set_val:.0f},{optimal[KEY_PA_CONF_A]:.0f},{optimal[KEY_PA_CONF_B]:.0f},{optimal[KEY_MEASURED]},{optimal[KEY_POWER]}\n")
    
    out.close()

    # we have parsed everything, find the most common combinations for each power level
    out = open("out/optimized.h", "w")
    if IS_LR2021:
      out.write("static const LR2021PaTableEntry_t paOptTableLf[RADIOLIB_LR2021_PA_TABLE_LEN] = {\n")
    else:
      out.write("static const SX126x::paTableEntry_t paOptimizedTable[RADIOLIB_SX126X_PA_TABLE_LEN] = {\n")
    for pwr in power_levels:
        if pwr - int(pwr) != 0:
          continue
        
        entries = filter_by_key('target', pwr, opt_settings)
        cfg_counts = Counter(e['paCfg'] for e in entries)
        print(f"Optimized {pwr:2.1f} dBm: {cfg_counts.most_common(1)[0][0]} ({cfg_counts.most_common(1)[0][1]}/{num_measurements} measurements)")
        cfg = cfg_counts.most_common(1)[0][0].split(',')
        out.write(f"  {{ .{KEY_PA_CONF_A} = {cfg[1]}, .{KEY_PA_CONF_B} = {cfg[2]}, .paVal = {cfg[0]} }}, // {pwr:.0f}\n")
    
    out.write("};\n")
    out.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python process.py <log_dir_path>")
        sys.exit(1)
    
    main(sys.argv[1])
