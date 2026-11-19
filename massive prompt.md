General Requirements from the instructor:
##################
Instructions


Submit your team’s lab report and materials. This assignment is only for Lab 2. It is separate from the term project.

The full task is in the attached lab sheet Lab 2 DES 26102025.docx. We also introduced it in the lab session. Starter TCP code is in DES_tcp_server_client_program (tcpServer.c, tcpClient.c) — plain networking only; you add DES and distributed send/receive on two machines.


What you must build

    Build a distributed DES app: each side creates a message, encrypts, sends, receives, decrypts, and shows the decrypted text (same as plaintext).
    Verify DES steps (debugger step mode, watched variables): initial permutation, inverse IP, expansion, round-key schedule (PC-1, shifts, PC-2), XOR with round key, S-boxes, P, XOR with left half, swap.
    Document how the two processes connect on different computers.
    Optional check: compare with the example in DES_LAB_example_26102025.docx (plaintext/key/ciphertext and avalanche).

Report (follow the lab sheet)

    Cover page (university, department, program, course, lab, subject, team members, lecturer, lab assistant, year, semester, city, country)
    Outline, problem definition, work done
    For the main tasks: explain your code and give debugger screenshots for DES steps, plus screenshots of create → encrypt → send → receive → decrypt → display
    Connection settings for the distributed setup
    Conclusion, references
    Appendix with source code

Submit one .zip or .rar file with the report, all source code (including your .c files and related project files), executables, and test examples. Do not submit only the report.

Where it fits your work, add a short conclusion, your opinion, and a comparison of choices you tried (e.g. networking setup, testing).
##################

DES_LAB_example_26102025.docx:
##################
A DES EXAMPLE
We now work through an example and consider some of its implications. Although you are not expected to duplicate the example by hand, you will find it informative to study the hex patterns that occur from one step to the next.
For this example, the plaintext is a hexadecimal palindrome. The plaintext, key, and resulting ciphertext are as follows:

Plaintext:	02468aceeca86420
Key:	0f1571c947d9e859
Ciphertext:	da02ce3a89ecac3b

Results
Table 4.2 shows the progression of the algorithm. The first row shows the 32-bit values of the left and right halves of data after the initial permutation. The next 16 rows show the results after each round. Also shown is the value of the 48-bit subkey generated for each round. Note that Li = Ri-1. The final row shows the left- and 
right-hand values after the inverse initial permutation. These two values combined form the ciphertext.
Table 4.2 DES Example

A DES EXAMPLE
We now work through an example and consider some of its implications. Although you are not expected to duplicate the example by hand, you will find it informative to study the hex patterns that occur from one step to the next.
For this example, the plaintext is a hexadecimal palindrome. The plaintext, key, and resulting ciphertext are as follows:

Plaintext:	02468aceeca86420
Key:	0f1571c947d9e859
Ciphertext:	da02ce3a89ecac3b

Results
Table 4.2 shows the progression of the algorithm. The first row shows the 32-bit values of the left and right halves of data after the initial permutation. The next 16 rows show the results after each round. Also shown is the value of the 48-bit subkey generated for each round. Note that Li = Ri-1. The final row shows the left- and 
right-hand values after the inverse initial permutation. These two values combined form the ciphertext.
Table 4.2 DES Example

Round:	Ki:	Li:	Ri:
IP		5a005a00	3cf03c0f
1	1e030f03080d2930	3cf03c0f	bad22845
2	0a31293432242318	bad22845	99e9b723
3	23072318201d0c1d	99e9b723	0bae3b9e
4	05261d3824311a20	0bae3b9e	42415649
5	3325340136002c25	42415649	18b3fa41
6	123a2d0d04262alc	18b3fa41	9616fe23
7	021f120blc130611	9616fe23	67117cf2
8	1c10372a2832002b	67117cf2	c11bfc09
9	04292a380c341f03	c11bfc09	887fbc6c
10	2703212607280403	887fbc6c	600f7e8b
11	2826390c31261504	600f7e8b	f596506e
12	12071c241a0a0f08	f596506e	738538b8
13	300935393c0d100b	738538b8	c6a62c4e
14	311e09231321182a	c6a62c4e	56b0bd75
15	283d3e0227072528	56b0bd75	75e8fd8f
16	2921080b13143025	75e8fd8f	25896490
IP-1		25896490	89ecac3b


Note: DES subkeys are shown as eight 6-bit values in hex format

THE AVALANCHE EFFECT IN DES
A desirable property of any encryption algorithm is that a small change in either the plaintext or the key should produce a significant change in the ciphertext. 
Change in one bit of the plaintext or one bit of the key should produce a change in many bits of the ciphertext. This is referred to as the avalanche effect.
Here, 1 bit change in the plaintext leads to 34 bit difference in the cipher-text. 1 bit change in the key leads to 35 bit difference in the cipher-text.
If the change were small, this might provide a way to reduce the size of the plaintext or key space to be searched.
Using the example from Table 4.2, Table 4.3 shows the result when the fourth bit of the plaintext is changed, so that the plaintext is 12468aceeca86420. The second column of the table shows the intermediate 64-bit values at the end of each round for the two plaintexts. The third column shows the number of bits that differ between the two intermediate values. The table shows that, after just three rounds, 18 bits differ between the two blocks. On completion, the two ciphertexts differ in 32 bit positions.
Table 4.4 shows a similar test using the original plaintext of with two keys that differ in only the fourth bit position: the original key, 0f1571c947d9e859, and the altered key, 1f1571c947d9e859. Again, the results show that about half of the bits in the ciphertext differ and that the avalanche effect is pronounced after just a few rounds.
Table 4.3  Avalanche Effect in DES: Change in Plaintext



Table 4.4  Avalanche Effect in DES: Change in Key




Round:		σ:
	02468aceeca86420	1
	12468aceeca86420	
		
1	3cf03c0fbad22845	1
	3cf03c0fbad32845	
		
2	bad2284599e9b723	5
	bad3284539a9b7a3	
		
3	99e9b7230bae3b9e	18
	39a9b7a3171cb8b3	
		
4	0bae3b9e42415649	34
	171cb8b3ccaca55e	
		
5	4241564918b3fa41	37
	ccaca55ed16c3653	
		
6	18b3fa419616fe23	33
	d16c3653cf402c68	
		
7	9616fe2367117cf2	32
	cf402c682b2cefbc	
		
8	67117cf2c11bfc09	33
	2b2cefbc99f91153	
		
9	c11bfc09887fbc6c	32
	99f911532eed7d94	
		
10	887fbc6c600f7e8b	34
	2eed7d94d0f23094	
		
11	600f7e8bf596506e	37
	d0f23094455da9c4	
		
12	f596506e738538b8	31
	455da9c47f6e3cf3	
		
13	738538b8c6a62c4e	29
	7f6e3cf34bc1a8d9	
		
14	c6a62c4e56b0bd75	33
	4bc1a8d91e07d409	
		
15	56b0bd7575e8fd8f	31
	1e07d4091ce2e6dc	
		
16	75e8fd8f25896490	32
	1ce2e6dc365e5f59	
		
IP-1	da02ce3a89ecac3b	32
	057cde97d7683f2a	

##################

Lab 2 DES 26102025.docx:
##################
Tasks
    1. Implement DES algorithm as a distributed application using two computers, each running a process able to create a message, encrypt it, send it, receive a message, decrypt it, and display it.
    2. Test it by checking correctness of the particular transformations used: 
        2.1.  Initial permutation
        2.2.  Inverse of the initial permutation
        2.3.  Expansion/permutation
        2.4.  Round key generation
            2.4.1.  Permuted choice 1 
            2.4.2. Left circular shifts schedule 
            2.4.3. Permuted choice 2
        2.5.  XOR with round key 
        2.6.  S-boxes
        2.7.  Permutation P after S-boxes
        2.8.  XOR with left half
        2.9.  Swap of the halves
        2.10. Create a message, encrypt, and send it to the Receiver process
        2.11. Receive a message from the Sender process, decrypt, and display it 
    3. Prepare a report on the work done.  It shall have
        3.1. Cover page (University, Department, Program, Course, Lab, Subject, Team members, Lecturer, Lab Assistant, Year, Semester, City, Country)
        3.2.  Outline
        3.3.  Problem definition
        3.4.  Work done
            3.4.1. For the problems 1, 2 considered, show your work done by explaining your code developed and presenting screenshots of the running in step mode of the debugger DES cipher with the tested variables watched. Provide screenshots showing creation of a message, encryption of it, sending, receiving, decryption, displaying the message decrypted (shall be the same as the plaintext message)
            3.4.2. Describe settings of the distributed system (how you organize connection of the processes running on different machines)
        3.5.  Conclusion
        3.6.  References
        3.7. Appendix with source codes
##################

When I talked with the instructor on how the report should be filed, he told me to make DES steps (like key generation or 48 to 32 bit trancuation) as individual method (or functions). Then later create a table like:
input to method , method name , method output , current DES step

Reminder that since we required to work with "two machines" this would mean running the machines inside docker or another vm method. meaning that two machines can be their each docker instance, speaking over LAN