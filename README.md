# canbusSniffer
Reads canbus packets from serial port.
Every packet require to have the structure as %PREFIX %ID %DLC %DATA.
  PREFIX  -   xAAx55xAAx55, to separate packets
  ID      -   3 bytes, eg '4b9'
  DL      -   1 byte, eg '3'
  DATA    -   max 8 bytes 'x00xFFxA5'
