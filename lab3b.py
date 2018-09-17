#!/usr/bin/python

import sys
import csv

def checkArgs():
    if len(sys.argv) != 2:
        print >> sys.stderr, "Error: invalid arguments."
        sys.exit(1);

def auditBlocks():
    filename = sys.argv[1]
    max_block_number = 0
    try:
        with open(filename, 'rb') as f:
            reader = csv.reader(f)
            bfree_list = []
            inode_list = []

            inodes_blocks_start = 5
            block_size = 1024
            total_num_inodes = 24
            inode_size = 128
            blocks_start = 8

            for line in reader:
                if line[0] == 'SUPERBLOCK':
                    max_block_number = int(line[1]) - 1
                    block_size = int(line[3])
                    inode_size = int(line[4])
                if line[0] == 'GROUP':
                    inodes_blocks_start = int(line[8])
                    total_num_inodes = int(line[3])
                    blocks_start = inodes_blocks_start + (total_num_inodes * inode_size / block_size)
                    # Round up!
                    if (total_num_inodes * inode_size % block_size != 0):
                        blocks_start += 1
                if line[0] == 'INODE':
                    for num in range(12, 24):
                        if int(line[num]) > max_block_number or int(line[num]) < 0:
                            print "INVALID BLOCK " + str(line[num]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(num-12)
                        elif 1 <= int(line[num]) and blocks_start > int(line[num]):
                            print "RESERVED BLOCK " + str(line[num]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(num-12)
                        elif int(line[num]) != 0:
                            inode_list.append(int(line[num]))

                    if int(line[24]) > max_block_number or int(line[24]) < 0:
                        print "INVALID INDIRECT BLOCK " + str(line[24]) + " IN INODE " + str(line[1]) + " AT OFFSET 12"
                    elif 1 <= int(line[24]) and blocks_start > int(line[24]):
                        print "RESERVED INDIRECT BLOCK " + str(line[24]) + " IN INODE " + str(line[1]) + " AT OFFSET 12"
                    elif int(line[24]) != 0:
                        inode_list.append(int(line[24]))

                    if int(line[25]) > max_block_number or int(line[25]) < 0:
                        print "INVALID DOUBLE INDIRECT BLOCK " + str(line[25]) + " IN INODE " + str(line[1]) + " AT OFFSET 268"
                    elif 1 <= int(line[25]) and blocks_start > int(line[25]):
                        print "RESERVED DOUBLE INDIRECT BLOCK " + str(line[25]) + " IN INODE " + str(line[1]) + " AT OFFSET 268"
                    elif int(line[25]) != 0:
                        inode_list.append(int(line[25]))

                    if int(line[26]) > max_block_number or int(line[26]) < 0:
                        print "INVALID TRIPLE INDIRECT BLOCK " + str(line[26]) + " IN INODE " + str(line[1]) + " AT OFFSET 65804"
                    elif 1 <= int(line[26]) and blocks_start > int(line[26]):
                        print "RESERVED TRIPLE INDIRECT BLOCK " + str(line[26]) + " IN INODE " + str(line[1]) + " AT OFFSET 65804"
                    elif int(line[26]) != 0:
                        inode_list.append(int(line[26]))

                if line[0] == 'INDIRECT':
                    if int(line[5]) > max_block_number or int(line[5]) < 0:
                        if int(line[2]) == 1:
                            print "INVALID BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 2:
                            print "INVALID INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 3:
                            print "INVALID DOUBLE INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                    elif 1 <= int(line[5]) and blocks_start > int(line[5]):
                        if int(line[2]) == 1:
                            print "RESERVED BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 2:
                            print "RESERVED INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 3:
                            print "RESERVED DOUBLE INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                    elif int(line[5]) != 0:
                        inode_list.append(int(line[5]))

                if line[0] == 'BFREE':
                    bfree_list.append(int(line[1]))


            for num in range(blocks_start, max_block_number + 1):
                if num not in bfree_list and num not in inode_list:
                    print "UNREFERENCED BLOCK " + str(num)
                if num in bfree_list and num in inode_list:
                    print "ALLOCATED BLOCK " + str(num) + " ON FREELIST"

            duplicates = []
            for num1 in range(0, len(inode_list)):
                for num2 in range(num1 + 1, len(inode_list)):
                    if inode_list[num1] == inode_list[num2]:
                        duplicates.append(inode_list[num1])

            f.seek(0, 0)
            reader = csv.reader(f)
            for line in reader:
                if line[0] == 'INODE':
                    for num in range(12, 24):
                        if int(line[num]) in duplicates:
                            print "DUPLICATE BLOCK " + str(line[num]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(num-12)

                    if int(line[24]) in duplicates:
                        print "DUPLICATE INDIRECT BLOCK " + str(line[24]) + " IN INODE " + str(line[1]) + " AT OFFSET 12"

                    if int(line[25]) in duplicates:
                        print "DUPLICATE DOUBLE INDIRECT BLOCK " + str(line[25]) + " IN INODE " + str(line[1]) + " AT OFFSET 268"

                    if int(line[26]) in duplicates:
                        print "DUPLICATE TRIPLE INDIRECT BLOCK " + str(line[26]) + " IN INODE " + str(line[1]) + " AT OFFSET 65804"

                if line[0] == 'INDIRECT':
                    if int(line[5]) in duplicates:
                        if int(line[2]) == 1:
                            print "DUPLICATE BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 2:
                            print "DUPLICATE INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])
                        if int(line[2]) == 3:
                            print "DUPLICATE DOUBLE INDIRECT BLOCK " + str(line[5]) + " IN INODE " + str(line[1]) + " AT OFFSET " + str(line[3])

    except IOError as e:
        print >> sys.stderr, "Error: can't read from file ", filename
        sys.exit(1)

def auditInodes():
    filename = sys.argv[1]
    max_block_number = 0
    try:
        with open(filename, 'rb') as f:
            reader = csv.reader(f)
            ifree_list = []         # Inodes on free list
            inode_list = []         # Allocated inodes
            total_num_inodes = 24   # In case SUPERBLOCK/GROUP report is not found
            first_inode_num = 11    # In case SUPERBLOCK report is not found

            for line in reader:
                if line[0] == 'SUPERBLOCK':
                    # Set total number of inodes and first inode number
                    total_num_inodes = int(line[2])
                    first_inode_num = int(line[7])
                if line[0] == 'GROUP':
                    # Set total number of inodes
                    total_num_inodes = int(line[3])  # Redundant (just in case SUPERBLOCK report is not found)
                if line[0] == 'INODE':
                    # Add inode numbers of allocated inodes to inode_list
                    inode_list.append(int(line[1]))
                if line[0] == 'IFREE':
                    # Add inode numbers of free inodes to ifree_list
                    ifree_list.append(int(line[1]))

            # If an inode number is in both inode_list and ifree_list, then
            # it should be reported as ALLOCATED + ON FREELIST.
            for num1 in range(0, len(inode_list)):
                if inode_list[num1] in ifree_list:
                    print "ALLOCATED INODE " + str(inode_list[num1]) + " ON FREELIST"

            # If an inode number is NOT in either inode_list or ifree_list, then
            # it should be reported as UNALLOCATED + NOT ON FREELIST.
            for num1 in range(first_inode_num, total_num_inodes + 1):
                if num1 not in inode_list and num1 not in ifree_list:
                    print "UNALLOCATED INODE " + str(num1) + " NOT ON FREELIST"

    except IOError as e:
        print >> sys.stderr, "Error: can't read from file ", filename
        sys.exit(1)

def auditDirents():
    filename = sys.argv[1]
    max_block_number = 0
    try:
        with open(filename, 'rb') as f:
            reader = csv.reader(f)
            refcounts = {}          # Map: inode number -> # of references by DIRENTs
            linkcounts = {}         # Map: inode number -> linkcount in INODE summary (allocated inodes)
            total_num_inodes = 24   # In case SUPERBLOCK/GROUP report is not found
            first_inode_num = 11    # In case SUPERBLOCK report is not found
            dir_list = []           # inode numbers of directories
            parent = {}               # Map: directory inode numbers -> list of directories inside that directory
            for line in reader:
                if line[0] == 'SUPERBLOCK':
                    # Set total number of inodes and first inode number
                    total_num_inodes = int(line[2])
                    first_inode_num = int(line[7])
                if line[0] == 'GROUP':
                    # Set total number of inodes
                    total_num_inodes = int(line[3])  # Redundant (just in case SUPERBLOCK report is not found)
                if line[0] == 'INODE':
                    # Add dict entry: <inode number, linkcount>
                    linkcounts[int(line[1])] = int(line[6])

                    # Add to list of inode numbers of directories
                    if str(line[2]) == 'd':
                        dir_list.append(int(line[1]))

                if line[0] == 'DIRENT':
                    # Either update old entry in dict or add a new one: <inode number, reference count>
                    ref_inode_num = int(line[3])
                    if ref_inode_num in refcounts:
                        refcounts[ref_inode_num] = refcounts[ref_inode_num] + 1
                    else:
                        refcounts[ref_inode_num] = 1

                    # Build the map (parent) that we will use later to determine a directory's parent directory.
                    inode_num = int(line[1])
                    if line[6] != "'.'" and line[6] != "'..'" and int(line[3]) in dir_list:
                        # dict entry does not exist
                        if inode_num not in parent:
                            parent[inode_num] = [int(line[3])]
                        # dict entry already exists
                        else:
                            parent[inode_num].append(int(line[3]))

            for key, value in linkcounts.items():
                # Report mismatch between inode linkcount and reference count
                if key in refcounts:
                    if value != refcounts[key]:
                        print "INODE " + str(key) + " HAS " + str(refcounts[key]) + " LINKS BUT LINKCOUNT IS " + str(value)
                # Report unreferenced inodes
                else:
                    print "INODE " + str(key) + " HAS 0 LINKS BUT LINKCOUNT IS " + str(value)

            # Iterate through the entire .csv file again
            f.seek(0, 0)
            reader = csv.reader(f)
            for line in reader:
                if line[0] == 'DIRENT':
                    inode_num = int(line[1])

                    # Report references to unallocated or invalid inodes (check if invalid first)
                    if int(line[3]) < 1 or int(line[3]) > total_num_inodes:
                        print "DIRECTORY INODE " + str(line[1]) + " NAME " + line[6] + " INVALID INODE " + str(line[3])
                    elif int(line[3]) not in linkcounts:
                        print "DIRECTORY INODE " + str(line[1]) + " NAME " + line[6] + " UNALLOCATED INODE " + str(line[3])
                   
                    # Report incorrect '.' and '..' links
                    if line[6] == "'.'":
                        # "Parent inode number" from DIRENT summary should match "inode number of referenced file"
                        if line[1] != line[3]:
                            print "DIRECTORY INODE " + str(line[1]) + " NAME " + line[6] + \
                            " LINK TO INODE " + str(line[3]) + " SHOULD BE " + str(line[1])
                    if line[6] == "'..'":
                        # Root directory's parent should be root directory
                        if inode_num == 2 and int(line[3]) != 2:
                            print "DIRECTORY INODE 2 NAME " + line[6] + \
                            " LINK TO INODE " + str(line[3]) + " SHOULD BE 2"
                            continue

                        for key, value in parent.items():
                            if inode_num in value:
                                if int(line[3]) != key:
                                    print "DIRECTORY INODE " + str(inode_num) + " NAME " + line[6] + \
                                    " LINK TO INODE " + str(line[3]) + " SHOULD BE " + str(key)

    except IOError as e:
        print >> sys.stderr, "Error: can't read from file ", filename
        sys.exit(1)

def main():
    checkArgs()
    auditBlocks()
    auditInodes()
    auditDirents()

if __name__ == "__main__":
    main()
