# FileSystemAnalyzer
The c-program summarizes the superblock, inode, and directory information of an EXT2 filesystem. It prints this information in csv format to be used by the python script, which detects any errors in the filesystem such as invalid inodes, duplicate inodes, incorrect free blocks, and directories with incorrect reference counts.
