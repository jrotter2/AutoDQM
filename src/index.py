import os
import sys
import json
import time
import ROOT
import subprocess

import search
import AutoDQM

# Global dict for holding all run times
times = {}
cur_dir = os.getcwd()

# Recursively find unique name for function call
def get_name(name, counter):
    new_name = name + str(counter)
    if new_name in times:
        counter += 1
        return get_name(name, counter)
    else:
        return (new_name)

# Wrapper for timing functions
def timer(func):
    def wrapper(*args, **kwargs):
        t0 = time.time()
        result = func(*args, **kwargs)

        times[get_name(func.__name__, 0)] = (time.time() - t0)
        return result
    return wrapper

def get_response(t0, status, fail_reason, query, payload):
    duration = time.time() - t0
    return json.dumps( { "query": query, "start": t0, "duration":duration, "response": { "status": status, "fail_reason": str(fail_reason), "payload": times } } )

@timer
def compile_hists(new_dir):
    old_h = {}
    dir_list = os.listdir(new_dir)
    counter = 0
    for path in dir_list:
        f = ROOT.TFile(new_dir + "/" + path)
        trees = {1:{"tree":f.Get("TH2Fs"), "type":ROOT.TH2F, "hists":["hORecHits", "hOStrips", "hOWires"],
                                                             "wildcards":["hRHGlobal"]},
                 2:{"tree":f.Get("TH1Fs"), "type":ROOT.TH1F, "hists":["hSnhits", "hSnSegments", "hWirenGroupsTotal", "hStripNFired", "hRHnrechits"],
                                                             "wildcards":["hRHTimingAnode", "hRHTiming", "hWireTBin"]}
                 }

        for t_dict in trees.values():

            for event in t_dict["tree"]:
                path = str(event.FullName)
                name = str(event.Value.GetName())

                # Only look at muon paths
                if not ("CSC/CSCOfflineMonitor" in path): continue
                if type(event.Value) != t_dict["type"]: continue
                # Histogram Checks - don't plot unwanted hists
                passed = False
                if name in t_dict["hists"]: passed = True
                if not passed:
                    for wc in t_dict["wildcards"]:
                        if wc in name:
                            passed = True
                if not passed: continue


                if name not in old_h:
                    old_h[name] = event.Value.Clone(name)
                    old_h[name].SetDirectory(0)
                else:
                    old_h[name].Add(event.Value)

        f.Close()

    return old_h

@timer
def get_hists(fdir, rdir, data_id, ref_id, user_id):
    f_hists = compile_hists(fdir)
    r_hists = compile_hists(rdir)

    subprocess.check_call(["{0}/make_html.sh".format(cur_dir), "setup", user_id])

    AutoDQM.autodqm(f_hists, r_hists, data_id, ref_id, user_id)

    subprocess.check_call(["{0}/make_html.sh".format(cur_dir), "updt", user_id])

    return True, None

# Generates 'id' used to identify RelVal comparison plots
def get_id(sample, path):
    return (sample + "_" + path.split("/DQMIO")[0].split("_")[-1].split("-")[0])

# Generates run number for SingleMuon identification
def get_run(path):
    name = ""
    name_split = path.split("/000/")[1].split("/00000/")[0].split("/")
    if (len(name_split) > 1):
        name = int(name_split[0] + name_split[1])
    else:
        name = int(name_split[0] + "000")

    return name

@timer
def get_files(path, targ_dir, run=None):

    response = search.handle_query({"query":path, "type":"files", "short":False})
    data = response["response"]["payload"]
    xrd_args = ["{0}/get_xrd.sh".format(cur_dir), targ_dir]

    # Path to targ dir, used to check if files already exist
    old_dir = os.listdir(targ_dir)

    found = False
    download = False # True if download should occur (used in check if all files already downloaded) 
    for tfile in data:
        # Check if files already downloaded to targ_dir
        if run:
            # keep this check separate from run existance check so file is not appended in else statement
            if int(run) == get_run(tfile["name"]):
                if old_dir and tfile["name"].split("/")[-1] in old_dir: 
                    if download: continue
                    else:
                        download = False
                        continue
                found = True
                download = True
                xrd_args.append(tfile["name"])
        else:
            if old_dir and tfile["name"].split("/")[-1] in old_dir: 
                download = False
                continue
            found = True
            download = True
            xrd_args.append(tfile["name"])
    if not found:
        return False, "Files not found - {0}".format(targ_dir)
    else:
        if download:
            subprocess.check_call(xrd_args)
        return True, None

def check(is_success, fail_reason):
    if not is_success: raise Exception('Error: {0}'.format(fail_reason))
    else: return None

def handle_RelVal(args):
    
    # Values for tracking script's progress
    is_success = False
    fail_reason = None

    try:
        # Generate root files via bash subprocess
        if args["type"] == "retrieve_data":
            is_success, fail_reason = get_files(args["data_query"], "{0}/data/{1}".format(os.getcwd(), args["user_id"]))
            check(is_success, fail_reason)
        elif args["type"] == "retrieve_ref":
            is_success, fail_reason = get_files(args["ref_query"], "{0}/ref/{1}".format(os.getcwd(), args["user_id"]))
            check(is_success, fail_reason)

        elif args["type"] == "process":
            # Root files should now be in data and ref directories
            is_success, fail_reason = get_hists("{0}/data".format(cur_dir), "{0}/ref".format(cur_dir), get_id(args["data_info"], args["data_query"]), get_id(args["ref_info"], args["ref_query"]), args["user_id"])
            check(is_success, 'get_hists')

    except Exception as error:
        fail_reason = error
        return is_success, fail_reason

    return is_success, fail_reason

def handle_SingleMuon(args):

    # Values for tracking script's progress
    is_success = False
    fail_reason = None

    try:
        if args["type"] == "retrieve_data":
            # Generate root files via bash subprocess
            is_success, fail_reason = get_files(args["data_query"], "{0}/data/{1}".format(os.getcwd(), args["user_id"]), args["data_info"])
            check(is_success, fail_reason)
        elif args["type"] == "retrieve_ref":
            is_success, fail_reason = get_files(args["ref_query"], "{0}/ref/{1}".format(os.getcwd(), args["user_id"]), args["ref_info"])
            check(is_success, fail_reason)

        elif args["type"] == "process":
            # Root files should now be in data and ref directories
            is_success, fail_reason = get_hists("{0}/data/{1}".format(os.getcwd(), args["user_id"]), "{0}/ref/{1}".format(os.getcwd(), args["user_id"]), args["data_info"], args["ref_info"], args["user_id"])
            check(is_success, 'get_hists')

    except Exception as error:
        fail_reason = str(error)
        return is_success, fail_reason

    return is_success, fail_reason

def process_query(args):
    t0 = time.time()

    if args["sample"] == "RelVal":
        is_success, fail_reason = handle_RelVal(args)
    elif args["sample"] == "SingleMuon":
        is_success, fail_reason = handle_SingleMuon(args)
    else:
        return get_response(t0, "fail", "Sample not supported", args,  "Query failed")
    
    if is_success and fail_reason == None:
        return get_response(t0, "success", fail_reason, args,  "Query proccessed successfully")
    else:
        return get_response(t0, "fail", fail_reason, args,  "Query failed")

if __name__ == "__main__":
    # print(process_query(["0th_index_is__this_file.py","/RelValZMM_14/CMSSW_9_1_1_patch1-PU25ns_91X_upgrade2023_realistic_v3_D17PU140-v1/DQMIO", "/RelValZMM_14/CMSSW_9_3_0_pre3-PU25ns_92X_upgrade2023_realistic_v2_D17PU140-v2/DQMIO", "RelVal", "ZMM_14", "ZMM_14"]))
    # print process_query(["0th_indix_is_this_file.py", "SingleMuon", "300811", "/SingleMuon/Run2017C-PromptReco-v3/DQMIO", "301531", "/SingleMuon/Run2017C-PromptReco-v3/DQMIO"])
    # test = {"type":"retrieve_data","sample":"SingleMuon", "ref_info":"301531", "ref_query":"/SingleMuon/Run2017C-PromptReco-v3/DQMIO", "data_info":"301165", "data_query":"/SingleMuon/Run2017C-PromptReco-v1/DQMIO", "user_id":str(int(time.time()))}
    # print(process_query(test))

    args = json.loads(sys.argv[1])
    print(process_query(args))
