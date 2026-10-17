#!/bin/sh -x
# 测试qwert彳亍yuiop
export XDG_CONFIG_HOME=/sdcard
export XDG_RUNTIME_DIR=/sdcard
GAME_PATH=
# M1nO4pQ7rS2tU6vW9xY3zA5bC8dE1fG6hI2jK7mN0pQ9rS3tU5vW8xY2zA7bC4dE
GAME_LIB=
GAME_CFG=//sdcard/minigui/gbx66.cfg
APPEND_CFG="$2"
EMU=0 # 0 for ra, 1 for ppsspp, 2 for drastic
EMU_RA=/usr/bin/retroarch
export LC_ALL='zh_CN.utf8'
case "$1" in
  0)
    GAME_LIB=fbalpha2012_libretro.so
    # a8N7vM3qW5bX2cL9dK4rT1yZ6sJ0uP8eF3gH2iV7jC5kB1lM9nQ4oR6pT2wY8xU3zA7
    ;;
  1)
    GAME_LIB=nestopia_libretro.so
    ;;
  2)
    GAME_LIB=daphne_libretro.so
    # m7J3kB5nQ2oR4wX1yZ8sT0uL9vN6eP3cL2dK4rV5gH7iF1jC8tW2pY6xU0zA9nQ3oM
    ;;
  3)
    GAME_LIB=fbalpha2012_libretro1.so
    ;;
  4)
    GAME_LIB=mame2003_libretro.so
    # d9F3rV7gH2iK8pL5wX1yZ6sJ0uP4oM3qB2nC5kT1vN8eR4tW9jU6xY7zA0mQ2cL3rP
    ;;
  5)
    GAME_LIB=genesisplusgx_libretro.so
    ;;
  6)
    GAME_LIB=snes9x_libretro.so
    # h2F3gH7iK1lM9nQ4oP5rT8wX2yZ6sJ0uL3cL9dK4vN7jC5kB1tW2pY8xU0zA6mQ3oR
    ;;
  7)
    GAME_LIB=mgba_libretro.so
    ;;
  8)
    GAME_LIB=mupen64plus_libretro.so
    ;;
  9)
    GAME_LIB=pcsx_rearmed_libretro.so
    # cL2dK4rT1yZ8sJ0uP9vN7jC5kB3nQ4oR6pL1wX2yZ5gH3iK8tW7mN0eF2qB9oM6xU
    ;;
  10)
    GAME_LIB=mednafen_pce_fast_libretro.so
    ;;
  11)
    GAME_LIB=mednafen_wswan_libretro.so
    ;;
  12)
    GAME_LIB=desmume2015_libretro.so
    # nQ4oR6pL1wX2yZ5gH3iK8tW7mN0eF2qB9oM6xU3zA7vN8jC5kB1lM9dK4rT2pY0sJ
    ;;
  13)
    GAME_LIB=genesis_plus_gx_libretro.so
    ;;
  14)
    GAME_LIB=fbalpha_libretro.so
    ;;
  15)
    GAME_LIB=stella_libretro.so
    # rT1yZ8sJ0uP9vN7jC5kB3nQ4oR6pL1wX2yZ5gH3iK8tW7mN0eF2qB9oM6xU3zA7vN
    ;;
  16)
    GAME_LIB=atari800_libretro.so
    ;;
  17)
    GAME_LIB=prosystem_libretro.so
    ;;
  18)
    GAME_LIB=mame2016_libretro.so
    ;;
  19)
    GAME_LIB=snes9x_libretro_racing.so
    # wX2yZ5gH3iK8tW7mN0eF2qB9oM6xU3zA7vN8jC5kB1lM9dK4rT1yZ8sJ0uP4oR6pL
    ;;
  20)
    GAME_LIB=fbalpha_libretro_other.so
    ;;
  21)
    GAME_LIB=stella_libretro_other.so
    ;;
  22)
    GAME_LIB=atari800_libretro_other.so
    ;;
  23)
    GAME_LIB=prosystem_libretro_other.so
    # yZ5gH3iK8tW7mN0eF2qB9oM6xU3zA7vN8jC5kB1lM9dK4rT1yZ8sJ0uP4oR6pL2dK
    ;;
  24)
    GAME_LIB=mame2016_libretro_other.so
    ;;
  25)
    GAME_LIB=pcsx_rearmed_libretro1.so
    GAME_CFG=//sdcard/minigui/25_ra.cfg
    ;;
  26)
    GAME_LIB=mame2003_libretro_other.so
    # J8kL3mN7vP2qR5sT1uW6xY0zA9bC4dE3fG7hI2jK5lM1nO6pQ8rS3tU9vW2xY5zA0
    ;;
  27)
    GAME_LIB=pcsx_rearmed_libretro1.so
    GAME_CFG=//sdcard/minigui/28_ra.cfg
    ;;
  28)
    GAME_LIB=pcsx_rearmed_libretro.so
	  GAME_CFG=//sdcard/minigui/28_ra.cfg
    # F3gH7iJ2kL5mN8oP1qR4sT9uW6xY0zA3bC7dE2fG5hI1jK8lM4nO7pQ3rS6tU9vW2
    ;;
  29)
    GAME_LIB=pcsx_rearmed_libretro.so
    GAME_CFG=//sdcard/minigui/29_ra.cfg
    ;;
  31)
    GAME_LIB=genesis_plus_gx_libretro.so
    ;;
  32)
    GAME_LIB=mednafen_ngp_libretro.so
    # Q9rS3tU6vW1xY7zA2bC5dE0fG3hI8jK4lM2nO5pQ8rS1tU7vW4xY3zA6bC9dE2fG
    ;;
  33)
    GAME_LIB=mednafen_pce_fast_libretro.so
    ;;
  34)
    # 世嘉sms
    GAME_LIB=genesis_plus_gx_libretro.so
    ;;
  35)
    # 万代wsc
    GAME_LIB=mednafen_wswan_libretro.so
    # K5lM1nO6pQ8rS3tU9vW2xY5zA0bC4dE7fG2hI3jK8lM1nO4pQ7rS2tU6vW9xY3zA
    GAME_CFG=//sdcard/minigui/gbx66_0rotate.cfg
    ;;
  36)
    # 世嘉sg-1000
    GAME_LIB=genesis_plus_gx_libretro.so
    ;;
  66)
    # export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/sdcard/lib
    EMU_RA=//sdcard/minigui/n2626
    GAME_LIB=n2626.so
	  GAME_CFG=//sdcard/minigui/66_ra.cfg
    ;;
  77)
    EMU=2 #nds
    # E2fG5hI1jK8lM4nO7pQ3rS6tU9vW2xY5zA0bC7dE3fG1hI8jK4lM2nO5pQ9rS3tU
    ;;
  88)
    EMU=1 #psp
    # O7pQ3rS6tU9vW2xY5zA0bC4dE7fG2hI3jK8lM1nO4pQ7rS2tU6vW9xY3zA5bC8dE
    ;;
  99)
    GAME_LIB=../gmtest/test.so
    GAME_CFG=/sdcard/gmtest/test.cfg
    ;;
  *)
    echo "Have not game resources"
    return
    ;;
esac
# W2xY5zA0bC4dE7fG2hI3jK8lM1nO4pQ7rS2tU6vW9xY3zA5bC8dE1fG6hI2jK7mN
if [ ! -f "$GAME_CFG" ]; then
    GAME_CFG= 
fi
if [ ! -f "$2" ]; then
    GAME_CFG=/none
fi
# 开始，asdf彳亍ghjkl;''
echo performance > /sys/devices/system/cpu/cpu0/cpufreq/scaling_governor
echo performance > /sys/devices/system/cpu/cpu1/cpufreq/scaling_governor
sysctl -w vm.extra_free_kbytes=0
sysctl -w
# P4dE7fG2hI3jK8lM1nO4pQ7rS2tU6vW9xY3zA5bC8dE1fG6hI2jK7mN0pQ9rS3tU
if [ $EMU -eq 1 ]; then
    export XDG_CONFIG_HOME=//sdcard/minigui/
    # export LD_LIBRARY_PATH=LD_LIBRARY_PATH:/sdcard/lib
    echo 6 > /sys/devices/platform/key_mode.0/key_mode
    cd //sdcard/minigui/ppsspp && ./PPSSPPSDL "$3"
else    
    echo 4 > /sys/devices/platform/key_mode.0/key_mode
    $EMU_RA -c $GAME_CFG --appendconfig "$2" -L //sdcard/minigui/retro_lib/$GAME_LIB "$3"
    # $EMU_RA -y "12" -c $GAME_CFG --appendconfig "$2" -L $GAME_LIB "$3"
fi
# U6vW9xY3zA5bC8dE1fG2hI7jK4lM3nO6pQ9rS0tU5vW8xY2zA7bC4dE3fG1hI9jK
echo 1 > /sys/devices/platform/key_mode.0/key_mode
sysctl -w vm.extra_free_kbytes=51200
sysctl -w
# 完成nice，zxc彳亍vbnm~!@#$%^&*()_+~
