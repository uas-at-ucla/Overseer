import time
import board
import adafruit_mpu6050

i2c = board.I2C()  # defaults 0x68
mpu = adafruit_mpu6050.MPU6050(i2c)

temp_offset = 0

print("Acceleration: X:%.2f, Y: %.2f, Z: %.2f m/s^2" % (mpu.acceleration + temp_offset))
print("Gyro X:%.2f, Y: %.2f, Z: %.2f degrees/s" % (mpu.gyro))
print("Temperature: %.2f C" % mpu.temperature)
time.sleep(1)
