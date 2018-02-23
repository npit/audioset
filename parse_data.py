import os, argparse
import pandas, json
import itertools

"""
Parse downloaded audioset data
"""


# -----------------------------------------
def read_ground_truth(gt_file, class_names, ontology_file, quality_file, min_num_samples, input_classes = None, quality_threshold = 0.8):
    print("=========================================")
    # read quality information
    retained_classes = []
    if quality_threshold is None:
        quality_threshold = 0.8
    quality_info = pandas.read_csv(quality_file)
    q_ids, q_num_checked, q_num_true = quality_info["label_id"], quality_info["num_rated"],quality_info["num_true"]
    for id,num,true in zip(q_ids, q_num_checked, q_num_true ):
        if not true:
            continue
        quality = true/num
        if quality < quality_threshold:
            continue
        retained_classes.append(id)
    print("Kept %d classes with a quality threshold of %f" % (len(retained_classes), quality_threshold))
    if input_classes is not None:
        iclasses = pandas.read_csv(input_classes)
        input_classes = list(iclasses.icol(-1))
        retained_classes = [ r for r in retained_classes if r in input_classes]
        print("Limited to the %d classes specified from the input file" % len(input_classes))

    class_names = pandas.read_csv(class_names)
    ids_names, names_ids = {}, {}
    for (id,name) in zip(class_names["mid"], class_names["display_name"]):
        if id not in retained_classes:
            continue
        ids_names[id] = name
        names_ids[name] = id

    retained_names = [ids_names[i] for i in retained_classes]

    # populate ground truth data items per class
    ground_truth = pandas.read_csv(gt_file, skiprows=3, header=None, skipinitialspace=True, names="ids start end classes".split())
    video_ids = ground_truth["ids"]
    video_classes = [cl.split(",") for cl in ground_truth["classes"]]
    total_assigned_annotations = []

    videoids_classes = {}
    classes_videoids = {}
    for cl, data_id in zip(video_classes, video_ids):
        cl = [c for c in cl if c in retained_classes]
        # add a data instance to each class of the class set
        total_assigned_annotations.extend(cl)
        videoids_classes[data_id] = cl
        for c in cl:
            if c not in retained_classes:
                continue
            cname = ids_names[c]
            if cname not in classes_videoids:
                classes_videoids[cname] = []
            classes_videoids[cname].append(data_id)

    # read class ontology
    ontology = {}
    leafs = []
    num_non_leafs, num_with_restrictions = 0, 0
    with open(ontology_file) as f:
        list_data = json.load(f)
    for obj in list_data:
        name = obj['name']
        id = obj['id']
        # skip those dropped by the quality check
        if id not in retained_classes:
            continue
        if not obj["child_ids"]:
            leafs.append(id)
        ontology[id] = {n:obj[n] for n in obj if n != "id"}
        children = [c for c in ontology[id]["child_ids"] if c in retained_classes]
        ontology[id]["child_ids"] = children
        # update names
        if id not in ids_names:
            ids_names[id] = name
        if name not in names_ids:
            names_ids[name] = id
        if name not in classes_videoids:
            classes_videoids[name] = []

    print("Counted %d leaf classes in the ontology" % len(leafs))

    roots = ["Human sounds", "Animal", "Sounds of things", "Music", "Natural sounds", "Channel, environment and background"]
    roots  = [ r for r in roots if r in names_ids]
    for cl in retained_names:
        data = classes_videoids[cl]
        if not data:
            classes_videoids[cl] = count_data_per_class(cl, names_ids,ids_names, classes_videoids, ontology)

    # print data
    for cl in retained_names:
        print_data_per_class(cl,names_ids,ids_names,classes_videoids,ontology,"--", depth = None)
        #print()
    # not restricted
    leafs = [l for l in leafs if not ontology[l]["restrictions"]]
    print()
    print("Left with %d leaf classes after removing classes with restrictions." % len(leafs))
    # with samples
    if min_num_samples is not None:
        leafs = [l for l in leafs if len(classes_videoids[ids_names[l]]) >= min_num_samples]
    print("Left with %d leaf classes after removing classes with less examples than the min = %d." % (len(leafs),min_num_samples))
    # excluding the ones below
    exclude_explicit = ["Channel, environment and background"]
    exclude = []
    for e in exclude_explicit:
        if e not in retained_classes:
            exclude_explicit.remove(e)
            continue
        children = get_children(ontology, names_ids[e])
        exclude.extend(children)

    exclude = list(set(exclude + exclude_explicit))
    leafs = [l for l in leafs if l not in exclude]

    for l in leafs:
        name = ids_names[l]
        print(l, name, len(classes_videoids[name]))
    print("Excluded %d classes from %d explicit exclusions" % (len(exclude),  len(exclude_explicit)))
    print("Left with %d leaf classes after explicitly removing %d classes and their children." % (len(leafs),len(exclude_explicit)))

    if input_classes is not None:
        assert all([ c in leafs for c in input_classes] + [c in input_classes for c in leafs]), "Leaf mismatch with input classes"
    print("Done.")
    return (cl, names_ids,ids_names, classes_videoids, videoids_classes, ontology, leafs)

def get_children(ontology, id):

    cids = ontology[id]["child_ids"]
    for c in cids:
        cids.extend(get_children(ontology,c))
    return cids

def print_data_per_class(name, names_ids, ids_names, classes_videoids, ontology, indent, depth=None):
    if not classes_videoids[name]:
        return
    id = names_ids[name]
    suff=""
    if ontology[id]["restrictions"]:
        suff = "*".join(ontology[id]["restrictions"])
        suff = "XXX"
    print("\n",indent + suff, "["+name+"]["+id+"]",len(classes_videoids[name])," ",end="")
    if "child_ids" not in ontology[id]:
        return

    if depth is None or depth > 0:
        if depth is not None:
            depth -= 1
        for cid in ontology[id]["child_ids"]:
            child_name = ids_names[cid]
            print_data_per_class(child_name,names_ids,ids_names,classes_videoids,ontology,indent + indent, depth)
    else:
        # print up to depth, aggregate children if finished.
        total = 0
        numkids = 0
        for cid in ontology[id]["child_ids"]:
            child_name = ids_names[cid]
            total += len(classes_videoids[child_name])
            numkids +=1
        print("aggregated %d kids:" % numkids,total,end="")

def count_data_per_class(name, names_ids, ids_names, classes_videoids, ontology):
    # fill up num data up to roots
    datalist = []
    id = names_ids[name]
    children = ontology[id]["child_ids"]
    for cid in children:
        child_name = ids_names[cid]
        if not classes_videoids[child_name]:
            classes_videoids[child_name] = count_data_per_class(child_name, names_ids,ids_names,classes_videoids,ontology)
        #print("Child of",name,":",child_name, classes_videoids[child_name])
        datalist.extend(classes_videoids[child_name])
    if not classes_videoids[name]:
        classes_videoids[name] = datalist
    else:
        if classes_videoids[name] != datalist:
            print("Existing and computed list mismatch for", name)
    return datalist

# -----------------------------------------

def read_downloaded_data(data_folder, classes_videoids, videoids_classes, ids_names, class_set_to_use, min_num_samples, outfilename,  empty_video_ids_file):
    print("=========================================")
    print("Checking downloaded data in",data_folder,"with %d classes to use:" % len(class_set_to_use))

    empty_video_ids = []
    if empty_video_ids_file is not None:
        empty_video_ids = pandas.read_csv(empty_video_ids_file, header=None)
        empty_video_ids = list(empty_video_ids.iloc[:,-1])
        print("Loaded %d video ids to discard" % len(empty_video_ids))

    # read downloaded data
    multiclass_ids = []
    skipped_ids = []
    data_to_classes = {}
    classes_to_data = {}
    downloaded_ids = []
    all_video_folders = os.listdir(data_folder)
    num_downloaded_data = len(all_video_folders)
    print("%d video folders in the path" % num_downloaded_data)
    for item_id in all_video_folders:
        if item_id in empty_video_ids:
            continue
        # get video class
        downloaded_ids.append(item_id)
        class_id = list(filter(lambda x : x in class_set_to_use, videoids_classes[item_id]))
        item_classnames = [ids_names[i] for i in class_id]
        if not item_classnames:
            skipped_ids.append(item_id)
            continue
        if len(class_id) > 1:
            multiclass_ids.append(item_id)
            continue
        class_id = class_id[0]

        # add to accumulation
        if class_id not in classes_to_data:
            classes_to_data[class_id] = []
        if item_id not in data_to_classes:
            data_to_classes[item_id] = []
        data_to_classes[item_id].append(class_id)
        classes_to_data[class_id].append(item_id)

    print("Read %d/%d items from the data path" % (len(downloaded_ids), num_downloaded_data))
    print("Skipped %d/%d irrelevant class videos" % (len(skipped_ids), num_downloaded_data))
    print("Skipped %d/%d multiclass videos" % (len(multiclass_ids), num_downloaded_data))
    not_downloaded = [id for id in videoids_classes if id not in downloaded_ids]
    not_in_gt = [id for id in downloaded_ids if id not in videoids_classes]
    print("Not downloaded: %d / %d items" % (len(not_downloaded),len(videoids_classes)))
    print("Not in gt: %d / %d items" % (len(not_in_gt),len(downloaded_ids)))
    print("Downloaded %d/%d relevant videos." % (len(data_to_classes),num_downloaded_data))

    print("Samples per data:")
    class_order = sorted(classes_to_data, key = lambda d : len(classes_to_data[d]))
    for i,cl in enumerate(class_order):
        print(1+i,"/",len(class_order),"|",cl,":",ids_names[cl],len(classes_to_data[cl]),classes_to_data[cl][:5])
    if min_num_samples is not None:
        retained_classes = [c for c in classes_to_data if len(classes_to_data[c]) >= min_num_samples]
        print("Retained %d/%d classes having at least %d samples." % (len(retained_classes),len(classes_to_data), min_num_samples))
        classes_to_data = {c:classes_to_data[c] for c in retained_classes}
        data_to_classes = {d:data_to_classes[d] for d in data_to_classes if [c in retained_classes for c in data_to_classes[d] if c in retained_classes] }
        print("Retained %d/%d downloaded videos having at least %d samples." % (len(data_to_classes),num_downloaded_data,min_num_samples))

    class_order = sorted(classes_to_data, key = lambda d : len(classes_to_data[d]))
    total_data = sum([len(classes_to_data[c]) for c in classes_to_data])
    print("Total number of videos for the retained %d classes:" % len(classes_to_data),total_data)
    print("*Final* samples per data:")
    for i,cl in enumerate(class_order):
        print(1+i,"/",len(class_order),"|",cl,":",ids_names[cl],len(classes_to_data[cl]),classes_to_data[cl][:5])

    # write stuff
    # resulting classes
    df = pandas.DataFrame(class_order)
    print("Writing resulting classes to",outfilename)
    df.to_csv(outfilename)

    # video paths
    pathsfile = outfilename + ".paths"
    print("Writing paths file to", pathsfile)
    with open(pathsfile, "w") as f:
        for class_index, cl in enumerate(class_order):
            for id in classes_to_data[cl]:
                f.write("%s %d\n" % (id, class_index))

    # class ids/names/idxs
    print("Writing class index file to", pathsfile + ".classidx")
    with open(pathsfile + ".classidx", "w") as f:
        for class_index, class_id in enumerate(class_order):
            classname = ids_names[cl]
            f.write("%s,%s,%d\n" % (class_id, classname, class_index))

if __name__ == "__main__":
    # parse arguments
    parser = argparse.ArgumentParser()
    parser.add_argument("data_folder")
    parser.add_argument("ground_truth")
    parser.add_argument("ontology")
    parser.add_argument("class_names")
    parser.add_argument("quality_file")
    parser.add_argument("--min_samples", type=int)
    parser.add_argument("--input_classes")
    parser.add_argument("--quality_threshold", type=float)
    parser.add_argument("--empty_video_ids")
    args = parser.parse_args()

    # read ground truth data:
    # read classes
    print("Building ontology tree")
    #tree = get_ontology_tree(args.ontology)
    #tree.print()
    roots, names_ids,ids_names, classes_videoids, videoids_classes, ontology, class_set_to_use =\
        read_ground_truth(args.ground_truth, args.class_names, args.ontology, args.quality_file, args.min_samples, args.input_classes, args.quality_threshold)

    iclasses_str = "" if args.input_classes is None else "_[%s]" % os.path.basename(args.input_classes)
    outfilename = "classes-out%s_q%1.2fm%d.csv" % (iclasses_str, args.quality_threshold, args.min_samples)
    read_downloaded_data(args.data_folder, classes_videoids, videoids_classes, ids_names, class_set_to_use, args.min_samples,  outfilename, args.empty_video_ids)


