#%%
from pycomm3 import LogixDriver
import time
import numpy as np


with LogixDriver('192.168.10.1') as plc:
    print(plc.info)
    print()

    test_freqs = []
    success_rates = []
    time_per_query = []
    time_per_write = []
    time_per_read = []
    time_per_query_sd = []
    time_per_write_sd = []
    time_per_read_sd  = []
    n_samples = 1000
    test_value_range = (0,100000000)
    frequency_test_range = (200,10000)
    n_frequencies = 10


    for x in range(n_frequencies):
        test_freq = round(x**2)

        print(f"test {x}: {n_samples} samples... ", end="")

        query_times = []
        write_times = []
        read_times = []

        failures = 0
        for test_value in np.linspace(*test_value_range, n_samples):
            start = time.perf_counter()
            test_value = int(test_value)
            start_write = time.perf_counter()
            plc.write("ifm_vpu2",test_value)
            write_times.append(time.perf_counter()-start_write)
            # pause momentarily
            # time.sleep(1/test_freq)
            start_read = time.perf_counter()
            echo = plc.read("ifm_vpu2").value
            read_times.append(time.perf_counter()-start_read)
            if echo !=test_value:
                failures +=1
            query_times.append(time.perf_counter()-start)
            # print(f"sent: {test_value}, recieved: {echo}")

        time_per_query.append(np.average(query_times))
        time_per_write.append(np.average(write_times))
        time_per_read.append(np.average(read_times))
        time_per_query_sd.append(np.std(query_times))
        time_per_write_sd.append(np.std(write_times))
        time_per_read_sd.append(np.std(read_times))

        success_rate = (n_samples-failures)/n_samples
        print(f"{round(success_rate*100,3)}% read/writes successfull... ", end = "")
        print(f"result: {round(1/(np.average(query_times)))} IOps")
# round(1/(np.std(time_per_query)))

        test_freqs.append(test_freq)
        success_rates.append(success_rate)

# %%
print(time_per_query)
print(time_per_write)
print(time_per_read)
# %%
#%%
from pycomm3 import LogixDriver
import time
import numpy as np


with LogixDriver('192.168.10.1') as plc:
    print(plc.info)
    print()

    test_freqs = []
    success_rates = []
    time_per_query = []
    time_per_write = []
    time_per_read = []
    time_per_query_sd = []
    time_per_write_sd = []
    time_per_read_sd  = []
    n_samples = 5
    test_value_range = (0,100000000)
    frequency_test_range = (200,10000)
    n_frequencies = 10
    tag_name = "ifm_from_vpu"


    for x in range(n_frequencies):
        test_freq = round(x**2)

        print(f"test {x}: {n_samples} samples... ", end="")

        query_times = []
        write_times = []
        read_times = []

        failures = 0
        for test_value in np.linspace(*test_value_range, n_samples):
            start = time.perf_counter()
            test_value = (int(test_value))
            start_write = time.perf_counter()
            plc.write(tag_name,test_value)
            write_times.append(time.perf_counter()-start_write)
            # pause momentarily
            # time.sleep(.01)
            start_read = time.perf_counter()
            echo = plc.read(tag_name).value
            read_times.append(time.perf_counter()-start_read)
            if echo !=test_value:
                failures +=1
            query_times.append(time.perf_counter()-start)
            print(f"sent: {test_value}, recieved: {echo}")

        time_per_query.append(np.average(query_times))
        time_per_write.append(np.average(write_times))
        time_per_read.append(np.average(read_times))
        time_per_query_sd.append(np.std(query_times))
        time_per_write_sd.append(np.std(write_times))
        time_per_read_sd.append(np.std(read_times))

        success_rate = (n_samples-failures)/n_samples
        print(f"{round(success_rate*100,3)}% read/writes successfull... ", end = "")
        print(f"result: {round(1/(np.average(query_times)))} IOps")
# round(1/(np.std(time_per_query)))

        test_freqs.append(test_freq)
        success_rates.append(success_rate)


# %%



#%%
from pycomm3 import LogixDriver
import time
import numpy as np
from pprint import pprint

with LogixDriver('192.168.10.1') as plc:
    # plc
    # pprint(plc.read("test_real"))
    # pprint(plc.read("aoi_o3r_test"))
    for x in range(100000):
        start = time.perf_counter() 

        plc.write("ifm_o3r_vpu_signal",x%2*1)
        time.sleep(1)
        print(x%2)
        print(round((time.perf_counter()-start)*1000))
    # plc.write("aoi_mul_test",())
# %%
import time
import numpy as np
from pprint import pprint

# %%