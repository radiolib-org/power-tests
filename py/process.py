import csv
import os
from typing import List, Dict
from collections import Counter 

KEY_SET = "Set [dBm]"
KEY_MEASURED = "Measured [dBm]"
KEY_POWER = "Power [mW]"

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
    out = open("out/optimized.csv", "w")
    out.write(f"Pout,{KEY_SET},paDutyCycle,hpMax,{KEY_MEASURED},{KEY_POWER}\n")
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
        num_measurements += 1
        
        # get the configured power levels
        power_levels = get_unique_values(KEY_SET, data)

        for pwr in power_levels:
            # find the actual measured value with the default PA configuration, this is the reference
            entries = filter_by_key(KEY_SET, pwr, data)
            entries = filter_by_key("paDutyCycle", 4, entries)
            entries = filter_by_key("hpMax", 7, entries)
            ref_level = entries[0][KEY_MEASURED]
            ref_power = entries[0][KEY_POWER]
        
            # find settings that produce something close to this reference value and sort them by power consumption
            entries = filter_by_range(KEY_MEASURED, ref_level, 0, 0.2, data)
            entries.sort(key=lambda x: x[KEY_POWER])
            optimal = entries[0]
            optimal['target'] = pwr
            optimal['paCfg'] = f"{optimal[KEY_SET]:.0f},{optimal['paDutyCycle']:.0f},{optimal['hpMax']:.0f}"
            opt_settings.append(optimal)

            # the first one is the result
            saving = 100 * (ref_power - optimal[KEY_POWER]) / ref_power
            #print(f"Optimized {pwr:2.0f} dBm: actual={optimal[KEY_MEASURED]} (was {ref_level:.2f}) Power: {ref_power} -> {optimal[KEY_POWER]} (-{saving:.2f}%)")
            
            # dump it to file for further analysis
            out.write(f"{pwr:.0f},{optimal[KEY_SET]:.0f},{optimal['paDutyCycle']:.0f},{optimal['hpMax']:.0f},{optimal[KEY_MEASURED]},{optimal[KEY_POWER]}\n")
    
    out.close()

    # we have parsed everything, find the most common combinations for each power level
    out = open("out/optimized.h", "w")
    out.write("const SX126x::paTableEntry_t paOptTable[32] = {\n")
    for pwr in power_levels:
        entries = filter_by_key('target', pwr, opt_settings)
        cfg_counts = Counter(e['paCfg'] for e in entries)
        print(f"Optimized {pwr:2.0f} dBm: {cfg_counts.most_common(1)[0][0]} ({cfg_counts.most_common(1)[0][1]}/{num_measurements} measurements)")
        cfg = cfg_counts.most_common(1)[0][0].split(',')
        out.write(f"  {{ .paDutyCycle = {cfg[1]}, .hpMax = {cfg[2]}, .paVal = {cfg[0]} }},\n")
    
    out.write("};\n")
    out.close()

if __name__ == "__main__":
    import sys
    if len(sys.argv) != 2:
        print("Usage: python script.py <log_dir_path>")
        sys.exit(1)
    
    main(sys.argv[1])
