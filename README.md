# canbusSniffer
Python code. Reads canbus packets from serial port connected to Arduino.
Every packet has a structure ID DLC DATA SUFFIX.
  ID      -   3 bytes, eg '4b9'
  DL      -   1 byte, eg '3'
  DATA    -   max 8 bytes 'x00xFFxA5'
  SUFFIX  -   xAAx55xAAx55, to separate packets
