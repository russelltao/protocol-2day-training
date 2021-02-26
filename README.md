
网络协议2天集训

# 抓包工具安装

## Wireshark
wireshark[下载地址](https://www.wireshark.org/#download)

## Tcpdump
1. CentOS
``` sh
yum install tcpdump -y
```

2. Ubuntu
``` sh
apt-get install tcpdump -y
```

# k8s抓包测试环境

## 查看虚拟网卡veth pair

### 查看网桥cni0上的虚拟网卡
``` sh
[master]# yum install bridge-utils -y
[master]# brctl show
bridge name     bridge id               STP enabled     interfaces
cni0            8000.822a0551fe51       no              veth01d2bc26
                                                        veth1b7415be
                                                        veth48059492
                                                        veth6174f7d6
                                                        veth6a56ab55
                                                        vethf3807a14
                                                        vethfbd1eb75
docker0         8000.024218847f20       no
```

### 查找容器网卡对应的主机上veth pair

比如，容器tea-6fb46d899f-4zkt2的IP地址是10.244.0.60：
``` sh
[root@master conf]# kubectl describe pod tea-6fb46d899f-4zkt2 | grep IP
IP:           10.244.0.60
```

它的MAC地址是B2:AD:3A:6E:3A:4F，如下：
```
[root@master conf]# kubectl exec -it tea-6fb46d899f-4zkt2 -- sh
/ $ ip addr
3: eth0@if17: <BROADCAST,MULTICAST,UP,LOWER_UP,M-DOWN> mtu 1450 qdisc noqueue state UP 
    link/ether b2:ad:3a:6e:3a:4f brd ff:ff:ff:ff:ff:ff
    inet 10.244.0.60/24 brd 10.244.0.255 scope global eth0
       valid_lft forever preferred_lft forever
    inet6 fe80::b0ad:3aff:fe6e:3a4f/64 scope link 
       valid_lft forever preferred_lft forever
```
注意，它的eth0序号是17。那么，它对应的主机veth pair虚拟网卡就是vetha1f852ea：
```
[root@master wp]# ip link show | egrep "veth" | awk -F":" '{print $1": "$2}'
14:  veth120e0e5a@if3
15:  veth7bd66290@if3
16:  veth16a8de20@if3
17:  vetha1f852ea@if3
18:  veth715a2ef5@if3
19:  veth094652aa@if3
20:  veth7e9e92b7@if3
21:  vethb4a73525@if3
```
当需要抓包时，用tcpdump -i vetha1f852ea即可抓取到容器报文：
``` sh
[root@master wp]# tcpdump -i vetha1f852ea
tcpdump: verbose output suppressed, use -v or -vv for full protocol decode
listening on vetha1f852ea, link-type EN10MB (Ethernet), capture size 262144 bytes


19:51:49.847648 IP 10.244.0.60.54477 > 10.96.0.10.domain: 58561+ A? www.baidu.com.default.svc.cluster.local. (57)
19:51:49.847731 IP 10.244.0.60.54477 > 10.96.0.10.domain: 59710+ AAAA? www.baidu.com.default.svc.cluster.local. (57)
19:51:49.849113 IP 10.244.0.58.domain > 10.244.0.60.54477: 59710 NXDomain*- 0/1/0 (150)
19:51:49.849268 IP 10.244.0.58.domain > 10.244.0.60.54477: 58561 NXDomain*- 0/1/0 (150)
```

## 跨L3三层vxlan网络抓包
当172.27.0.11主机上访问172.27.16.10主机上的10.244.1.3容器时，IP、MAC地址的获取如下：
### Underlay层的IP与MAC地址
在源主机上执行ifconfig，从eth0上即可看到Underlay源IP为172.27.0.11，以及Underlay源MAC为52:54:00:c2:ee:db：
``` sh
[root@master wp]# ifconfig eth0
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 172.27.0.11  netmask 255.255.240.0  broadcast 172.27.15.255
        inet6 fe80::5054:ff:fec2:eedb  prefixlen 64  scopeid 0x20<link>
        ether 52:54:00:c2:ee:db  txqueuelen 1000  (Ethernet)
        RX packets 783420  bytes 872472212 (832.0 MiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 462834  bytes 135019947 (128.7 MiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0

```

在目的主机上执行同样步骤，获取到Underlay目的IP为172.27.16.10：
``` sh
[root@VM-16-10-centos ~]# ifconfig eth0
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 172.27.16.10  netmask 255.255.240.0  broadcast 172.27.31.255
        inet6 fe80::5054:ff:fe4e:502  prefixlen 64  scopeid 0x20<link>
        ether 52:54:00:4e:05:02  txqueuelen 1000  (Ethernet)
        RX packets 39103520  bytes 6692916434 (6.2 GiB)
        RX errors 0  dropped 0  overruns 0  frame 0
        TX packets 1169194048  bytes 117270853999 (109.2 GiB)
        TX errors 0  dropped 0 overruns 0  carrier 0  collisions 0
```
需要注意，**Underlay目的MAC并不是52:54:00:4e:05:02**！Underlay目的MAC实际上是交换机的MAC地址fe:ee:32:07:ea:07：
``` sh
[root@master net]# arp -v
Address                  HWtype  HWaddress           Flags Mask            Iface
gateway                  ether   fe:ee:32:07:ea:07   C                     eth0
```

这样，Underlay层的4个地址都已得到！

### Overlay层的IP与MAC地址

目标容器的IP地址是10.244.1.3，但MAC地址却不能是容器的MAC地址，而必须是flannel.1的地址，因为flannel程序需要将Underlay层剥离，同时修改Overlay层，所以目标MAC地址其实是2a:3c:a0:e1:a9:b6：
```
[root@master net]# arp -v
Address                  HWtype  HWaddress           Flags Mask            Iface
10.244.1.0               ether   2a:3c:a0:e1:a9:b6   CM                    flannel.1
```

而源IP地址与MAC要根据路由规则来。比如，访问10.244.1.3是通过flannel.1网卡进行的：
``` sh
[root@master net]# ip route
default via 172.27.0.1 dev eth0
10.244.1.0/24 via 10.244.1.0 dev flannel.1 onlink
172.27.0.0/20 dev eth0 proto kernel scope link src 172.27.0.11
```
而flannel.1虚拟网卡的IP地址则是10.244.0.0：
``` sh
[root@master net]# ifconfig flannel.1
flannel.1: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1450
        inet 10.244.0.0  netmask 255.255.255.255  broadcast 10.244.0.0
ether 8e:5c:79:80:cd:cc  txqueuelen 0  (Ethernet)
[root@master net]# ifconfig eth0
eth0: flags=4163<UP,BROADCAST,RUNNING,MULTICAST>  mtu 1500
        inet 172.27.0.11  netmask 255.255.240.0  broadcast 172.27.15.255
ether 52:54:00:c2:ee:db  txqueuelen 1000  (Ethernet)
```
它的MAC地址则是8e:5c:79:80:cd:cc。

# 常见网络编码

## ASCII编码
参见[wiki](https://zh.wikipedia.org/wiki/ASCII)，如果打不开，可以查看下表:
### 控制字符
二进制 | 十进制 | 十六进制 | 缩写 | Unicode表示法 | 脱出字符表示法 | 名称／意义
----|-----|------|----|--------|----|--------
0000 0000 | 0 | 00 | NUL | ␀ | ^@ | 空字符（Null）
0000 0001 | 1 | 01 | SOH | ␁ | ^A | 标题开始
0000 0010 | 2 | 02 | STX | ␂ | ^B | 本文开始
0000 0011 | 3 | 03 | ETX | ␃ | ^C | 本文结束
0000 0100 | 4 | 04 | EOT | ␄ | ^D | 传输结束
0000 0101 | 5 | 05 | ENQ | ␅ | ^E | 请求
0000 0110 | 6 | 06 | ACK | ␆ | ^F | 确认回应
0000 0111 | 7 | 07 | BEL | ␇ | ^G | 响铃
0000 1000 | 8 | 08 | BS | ␈ | ^H | 退格
0000 1001 | 9 | 09 | HT | ␉ | ^I | 水平定位符号
0000 1010 | 10 | 0A | LF | ␊ | ^J | 换行键
0000 1011 | 11 | 0B | VT | ␋ | ^K | 垂直定位符号
0000 1100 | 12 | 0C | FF | ␌ | ^L | 换页键
0000 1101 | 13 | 0D | CR | ␍ | ^M | CR (字符)
0000 1110 | 14 | 0E | SO | ␎ | ^N | 取消变换（Shift out）
0000 1111 | 15 | 0F | SI | ␏ | ^O | 启用变换（Shift in）
0001 0000 | 16 | 10 | DLE | ␐ | ^P | 跳出数据通讯
0001 0001 | 17 | 11 | DC1 | ␑ | ^Q | 设备控制一（XON 激活软件速度控制）
0001 0010 | 18 | 12 | DC2 | ␒ | ^R | 设备控制二
0001 0011 | 19 | 13 | DC3 | ␓ | ^S | 设备控制三（XOFF 停用软件速度控制）
0001 0100 | 20 | 14 | DC4 | ␔ | ^T | 设备控制四
0001 0101 | 21 | 15 | NAK | ␕ | ^U | 确认失败回应
0001 0110 | 22 | 16 | SYN | ␖ | ^V | 同步用暂停
0001 0111 | 23 | 17 | ETB | ␗ | ^W | 区块传输结束
0001 1000 | 24 | 18 | CAN | ␘ | ^X | 取消
0001 1001 | 25 | 19 | EM | ␙ | ^Y | 连线介质中断
0001 1010 | 26 | 1A | SUB | ␚ | ^Z | 替换
0001 1011 | 27 | 1B | ESC | ␛ | ^[ | 退出键
0001 1100 | 28 | 1C | FS | ␜ | ^\ | 文件分割符
0001 1101 | 29 | 1D | GS | ␝ | ^] | 组群分隔符
0001 1110 | 30 | 1E | RS | ␞ | ^^ | 记录分隔符
0001 1111 | 31 | 1F | US | ␟ | ^_ | 单元分隔符
0111 1111 | 127 | 7F | DEL | ␡ | ^? | Delete字符

### 可显示字符

二进制 | 十进制 | 十六进制 | 图形
----|-----|------|---
0010 0000 | 32 | 20 | (space)
0010 0001 | 33 | 21 | !
0010 0010 | 34 | 22 | "
0010 0011 | 35 | 23 | #
0010 0100 | 36 | 24 | $
0010 0101 | 37 | 25 | %
0010 0110 | 38 | 26 | &
0010 0111 | 39 | 27 | '
0010 1000 | 40 | 28 | (
0010 1001 | 41 | 29 | )
0010 1010 | 42 | 2A | *
0010 1011 | 43 | 2B | +
0010 1100 | 44 | 2C | ,
0010 1101 | 45 | 2D | -
0010 1110 | 46 | 2E | .
0010 1111 | 47 | 2F | /
0011 0000 | 48 | 30 | 0
0011 0001 | 49 | 31 | 1
0011 0010 | 50 | 32 | 2
0011 0011 | 51 | 33 | 3
0011 0100 | 52 | 34 | 4
0011 0101 | 53 | 35 | 5
0011 0110 | 54 | 36 | 6
0011 0111 | 55 | 37 | 7
0011 1000 | 56 | 38 | 8
0011 1001 | 57 | 39 | 9
0011 1010 | 58 | 3A | :
0011 1011 | 59 | 3B | ;
0011 1100 | 60 | 3C | <
0011 1101 | 61 | 3D | =
0011 1110 | 62 | 3E | >
0011 1111 | 63 | 3F | ?

二进制 | 十进制 | 十六进制 | 图形
----|-----|------|---
0100 0000 | 64 | 40 | @
0100 0001 | 65 | 41 | A
0100 0010 | 66 | 42 | B
0100 0011 | 67 | 43 | C
0100 0100 | 68 | 44 | D
0100 0101 | 69 | 45 | E
0100 0110 | 70 | 46 | F
0100 0111 | 71 | 47 | G
0100 1000 | 72 | 48 | H
0100 1001 | 73 | 49 | I
0100 1010 | 74 | 4A | J
0100 1011 | 75 | 4B | K
0100 1100 | 76 | 4C | L
0100 1101 | 77 | 4D | M
0100 1110 | 78 | 4E | N
0100 1111 | 79 | 4F | O
0101 0000 | 80 | 50 | P
0101 0001 | 81 | 51 | Q
0101 0010 | 82 | 52 | R
0101 0011 | 83 | 53 | S
0101 0100 | 84 | 54 | T
0101 0101 | 85 | 55 | U
0101 0110 | 86 | 56 | V
0101 0111 | 87 | 57 | W
0101 1000 | 88 | 58 | X
0101 1001 | 89 | 59 | Y
0101 1010 | 90 | 5A | Z
0101 1011 | 91 | 5B | [
0101 1100 | 92 | 5C | \
0101 1101 | 93 | 5D | ]
0101 1110 | 94 | 5E | ^
0101 1111 | 95 | 5F | _

二进制 | 十进制 | 十六进制 | 图形
----|-----|------|---
0110 0000 | 96 | 60 | `
0110 0001 | 97 | 61 | a
0110 0010 | 98 | 62 | b
0110 0011 | 99 | 63 | c
0110 0100 | 100 | 64 | d
0110 0101 | 101 | 65 | e
0110 0110 | 102 | 66 | f
0110 0111 | 103 | 67 | g
0110 1000 | 104 | 68 | h
0110 1001 | 105 | 69 | i
0110 1010 | 106 | 6A | j
0110 1011 | 107 | 6B | k
0110 1100 | 108 | 6C | l
0110 1101 | 109 | 6D | m
0110 1110 | 110 | 6E | n
0110 1111 | 111 | 6F | o
0111 0000 | 112 | 70 | p
0111 0001 | 113 | 71 | q
0111 0010 | 114 | 72 | r
0111 0011 | 115 | 73 | s
0111 0100 | 116 | 74 | t
0111 0101 | 117 | 75 | u
0111 0110 | 118 | 76 | v
0111 0111 | 119 | 77 | w
0111 1000 | 120 | 78 | x
0111 1001 | 121 | 79 | y
0111 1010 | 122 | 7A | z
0111 1011 | 123 | 7B | {
0111 1100 | 124 | 7C | |
0111 1101 | 125 | 7D | }
0111 1110 | 126 | 7E | ~




