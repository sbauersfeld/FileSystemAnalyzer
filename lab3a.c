#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/stat.h>
#include <fcntl.h>
#include <time.h>
#include "ext2_fs.h"

int fd;             // file descriptor of image file
struct ext2_super_block super;
struct ext2_group_desc group;
unsigned int bsize;
unsigned int array_counter = 0;
unsigned int inode_count;
int *inode_array;   // dynamically allocated array of allocated inodes

/** Process and print superblock information. */
void processSuperblock() {
    pread(fd, &super, sizeof(super), 1024);
    fprintf(stdout, "SUPERBLOCK,%d,%d,%d,%d,%d,%d,%d\n", super.s_blocks_count,
            super.s_inodes_count, 1024<<super.s_log_block_size,
            super.s_inode_size, super.s_blocks_per_group,
            super.s_inodes_per_group, super.s_first_ino);
}

/** Process and print block group information. */
void processGroup() {
    pread(fd, &group, sizeof(group), 2048);
    fprintf(stdout, "GROUP,%d,%d,%d,%d,%d,%d,%d,%d\n", 0, super.s_blocks_count,
            super.s_inodes_per_group, group.bg_free_blocks_count,
            group.bg_free_inodes_count, group.bg_block_bitmap, group.bg_inode_bitmap,
            group.bg_inode_table);
}

/** Process and print free block information. */
void processFreeBlocks() {
    bsize = 1024<<super.s_log_block_size;
    int bitmap_start = group.bg_block_bitmap * bsize;
    char buf;
    unsigned int i;
    /* Iteration through each byte. */
    for(i = 0; i <= (super.s_blocks_count/8); i++){
        pread(fd, &buf, 1, bitmap_start + i);
        int k = 0;
        /* Iterate through each bit, starting from the right side (LSb). */
        for(k = 0; k < 8; k++){
            /* If block # is past block count, stop. */
            if (8*i+k >= super.s_blocks_count)
                break;
            /* If the bit is 0, the block is free.*/
            if (~buf & 1){
                fprintf(stdout, "BFREE,%d\n", 8*i+k+1); // block # starts @ 1
            }
            buf=buf>>1;
        }
    }
}

/** Process and print free inode information. */
void processFreeInodes() {
    int id = group.bg_inode_bitmap;
    int inode_start=id*bsize;
    inode_count = super.s_inodes_count;
    inode_array = malloc(sizeof(int) * inode_count);
    /* Iterate through each byte. */
    unsigned int i;
    char buf;
    for(i = 0; i <= inode_count/8; i++){
        int k = 0;
        pread(fd, &buf, 1, inode_start+i);
        /* Iterature through each bit, starting from the right side (LSb). */
        for (k = 0; k < 8; k++){
            /* If inode # is past inode count, stop. */
            if ((unsigned int) 8*i+k >= inode_count)
                break;
            /* If the bit is 0, the inode is free.*/
            if (~buf & 1){
                fprintf(stdout, "IFREE,%d\n", 8*i+k+1); // inode # starts @ 1
            }
            /* Keep track of allocated inodes. */
            else {
                inode_array[array_counter] = 8*i+k+1;   // inode # starts @ 1
                array_counter++;
            }
            buf=buf>>1;
        }
    }
}

/**
 * Processes and prints directory entry information for a given block number
 * if that block number is not 0.
 */
void processDirents(__u32 block_id, __u32 parentInodeNumber) {
    /* Don't process null pointers (block ID == 0). */
    if (block_id == 0)
        return;

    unsigned int ctr = 0;
    struct ext2_dir_entry dirent;
    while (ctr != bsize) {
        pread(fd, &dirent, sizeof(dirent), block_id*bsize + ctr);

        char filename[dirent.name_len + 1];
        int k;
        for (k = 0; k < dirent.name_len; k++) {
            filename[k] = dirent.name[k];
        }
        filename[dirent.name_len] = '\0';

        if (dirent.inode != 0) {
            fprintf(stdout, "DIRENT,%d,%d,%d,%d,%d,'%s'\n",
                    parentInodeNumber, ctr, dirent.inode,
                    dirent.rec_len, dirent.name_len, filename);
        }
        ctr += dirent.rec_len;
    }
}

/** Processes and prints inode summary/directory entries/indirect blocks. */
void processInodeSummary() {
    /* Inode summary */
    int id=group.bg_inode_table;
    struct ext2_inode ino;
    char output_time1[32];
    char output_time2[32];
    char output_time3[32];
    unsigned int i;
    for (i = 0; i < array_counter; i++){
        pread(fd, &ino, sizeof(ino), bsize*id + (inode_array[i]-1)*sizeof(ino));
        if (ino.i_mode != 0 && ino.i_links_count != 0){
            char type = '?';
            if ((ino.i_mode & 0xA000) == 0xA000)
                type = 's';
            else if ((ino.i_mode & 0x8000) == 0x8000)
                type = 'f';
            else if ((ino.i_mode & 0x4000) == 0x4000)
                type = 'd';
            struct tm* time_value1;
	    time_t t0 = ino.i_ctime;
	    time_t t1 = ino.i_mtime;
            time_t t2 = ino.i_atime;
	    time_value1 = gmtime(&t0);
	    strftime(output_time1, 32, "%m/%d/%y %H:%M:%S", time_value1);
            time_value1 = gmtime(&t1);
            strftime(output_time2, 32, "%m/%d/%y %H:%M:%S", time_value1);
            time_value1 = gmtime(&t2);
            strftime(output_time3, 32, "%m/%d/%y %H:%M:%S", time_value1);
            fprintf(stdout, "INODE,%d,%c,%o,%d,%d,%d,%s,%s,%s,%d,%d",
                    inode_array[i], type, ino.i_mode&0x0fff, ino.i_uid,
                    ino.i_gid, ino.i_links_count, output_time1, output_time2,
                    output_time3, ino.i_size, ino.i_blocks);
            int j = 0;
            for (j = 0; j < 15; j++){
                fprintf(stdout, ",%d", ino.i_block[j]);
            }
            fprintf(stdout, "\n");

            if (type == 'd' || type == 'f') {
                /* Direct block directory entries */
                if (type == 'd') {
                    /* Scan the 12 direct pointers. */
                    int j;
                    for (j = 0; j < 12; j++) {
                        processDirents(ino.i_block[j], inode_array[i]);
                    }
                }

                /* Indirect block (13th entry) == 1024 B == 256 block IDs.
                   Scan the indirect block for 256 direct pointers. */
                __u32 ind_start = ino.i_block[12] * bsize;    // 13th entry start pos
                int k;
                __u32 block_id;
                if (ind_start != 0) {
                    for (k = 0; k < 256; k++) {
                        /* Get block ID */
                        pread(fd, &block_id, sizeof(block_id), ind_start + sizeof(block_id)*k);
                        /* Don't process null pointers. */
                        if (block_id == 0)
                            continue;
                        fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                inode_array[i], 1, k+12, ino.i_block[12], block_id);

                        /* Indirect block directory entries */
                        if (type == 'd')
                            processDirents(block_id, inode_array[i]);
                    }
                }

                /* Double indirect */
                __u32 dub_start = ino.i_block[13] * bsize;  // 14th entry start pos
                int a;
                __u32 dub_block_id;
                if (dub_start != 0) {
                    for (a = 0; a < 256; a++) {
                        pread(fd, &dub_block_id, sizeof(dub_block_id), dub_start + sizeof(dub_block_id)*a);
                        if (dub_block_id == 0)
                            continue;
                        fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                inode_array[i], 2, a+268, ino.i_block[13], dub_block_id);

                        int k;
                        __u32 block_id;
                        if (dub_block_id != 0) {
                            for (k = 0; k < 256; k++) {
                                /* Get block ID */
                                pread(fd, &block_id, sizeof(block_id), dub_block_id*bsize + sizeof(block_id)*k);

                                /* Don't process null pointers. */
                                if (block_id == 0)
                                    continue;
                                fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                        inode_array[i], 1, 256*a+268+k, dub_block_id, block_id);

                                /* Indirect block directory entries */
                                if (type == 'd')
                                    processDirents(block_id, inode_array[i]);
                            }
                        }
                    }
                }

                /* Triple indirect */
                __u32 trip_start = ino.i_block[14] * bsize; // 15th
                int b;
                __u32 trip_block_id;
                if (trip_start != 0) {

                    for (b = 0; b < 256; b++) {
                        pread(fd, &trip_block_id, sizeof(trip_block_id), trip_start + sizeof(trip_block_id)*b);
                        if (trip_block_id == 0)
                            continue;
                        fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                inode_array[i], 3, b+65804, ino.i_block[14], trip_block_id);

                        /* Double indirect */
                        dub_start = trip_block_id * bsize;  // 14th entry start pos
                        if (dub_start != 0) {
                            for (a = 0; a < 256; a++) {
                                pread(fd, &dub_block_id, sizeof(dub_block_id), dub_start + sizeof(dub_block_id)*a);
                                if (dub_block_id == 0)
                                    continue;
                                fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                        inode_array[i], 2, 256*b + a + 65804, trip_block_id, dub_block_id);

                                int k;
                                __u32 block_id;
                                if (dub_block_id != 0) {
                                    for (k = 0; k < 256; k++) {
                                        /* Get block ID */
                                        pread(fd, &block_id, sizeof(block_id), dub_block_id*bsize + sizeof(block_id)*k);

                                        /* Don't process null pointers. */
                                        if (block_id == 0)
                                            continue;
                                        fprintf(stdout, "INDIRECT,%d,%d,%d,%d,%d\n",
                                                inode_array[i], 1, 256*a + 65804+k + 256*256*b, dub_block_id, block_id);

                                        /* Indirect block directory entries */
                                        if (type == 'd')
                                            processDirents(block_id, inode_array[i]);
                                    }
                                }
                            }
                        }
                    }
                }
            }
        }
    }
}

int main(int argc, char** argv){
    /* Verify argument given. */
    if (argc != 2) {
        fprintf(stderr, "Error: incorrect arguments.\n");
        exit(1);
    }

    /* Open image file. */
    char* image = argv[1];
    fd = open(image, O_RDONLY);
    if (fd == -1) {
        fprintf(stderr, "Error: open() failed.\n");
        exit(1);
    }

    /* Process and print image file information. */
    processSuperblock();
    processGroup();
    processFreeBlocks();
    processFreeInodes();
    processInodeSummary();

    /* Free dynamically allocated memory. */
    if (inode_array)
        free(inode_array);
}

