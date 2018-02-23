import os
import argparse

parser=argparse.ArgumentParser()
parser.add_argument("input")
parser.add_argument("suffix")
parser.add_argument("--simulate",action="store_true")
args = parser.parse_args()

log = open("renaming_log.txt","w")

for folder in os.listdir(args.input):
    oldfolderpath = os.path.join(args.input, folder)
    print('old folder name:', oldfolderpath)

    undscores = [i for i in range(len(folder)) if folder[i] == "_"]
    folderpath = os.path.join(args.input,folder[:undscores[-2]])
    # format: blablabla_numeric1_numeric2
    print('new folder name:',folderpath)

    log.write("%s -> %s\n" % (oldfolderpath, folderpath))
    if not args.simulate:
        os.rename(oldfolderpath, folderpath)

    # rename the spectrogram images themeselves to numeric.extension
    spectros = os.listdir(folderpath)
    for s in spectros:
        spectropath_old = os.path.join(folderpath, s)
        if s.startswith("_segment"):
            spectroname_new =  s[8:]
            spectropath_new = os.path.join(folderpath, spectroname_new)
            print("\t",s,"->", spectropath_new)
            log.write("%s -> %s\n" % (spectropath_old, spectropath_new))
            if not args.simulate:
                os.rename(spectropath_old, spectropath_new)
        else:
            print("Does not start with 'segment' prefix!")
            log.close()
            exit(1)
    print()

log.close()
