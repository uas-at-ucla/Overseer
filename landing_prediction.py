# -*- coding: utf-8 -*-
"""landing_prediction.ipynb
/Users/lorraine/Downloads/landing_prediction.py
Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1F2ARHwkZGHdrVVJk-O3yoNYOrpx2ReCX

Landing-Prediction Code

Adapted by: Dave Ackerman's prediction.py

https://github.com/daveake/flextrak/blob/master/prediction.py
"""

from enum import Enum
import math

class FlightMode(Enum):
    fmIdle          = 0
    fmLaunched      = 1
    fmDescending    = 2
    fmLanded        = 3

class Delta():
    def __init__(self, latitude, longitude):
        self.latitude = latitude 
        self.longitude = longitude
        
class Predictor(object):
    def __init__(self, LandingAltitude, DefaultCDA):
        self.SlotSize = 100
        self.SlotCount = 60000 // self.SlotSize
        self.Deltas = []
        self.FlightMode = FlightMode.fmIdle
        self.PreviousPosition = {'time': '00:00:00', 'lat': 0.0, 'lon': 0.0, 'alt': 0, 'sats': 0, 'fixtype': 0}
        self.MinimumAltitude = 0
        self.MaximumAltitude = 0
        self.AscentRate = 0
        self.LandingAltitude = LandingAltitude
        self.LandingLatitude = 0.0
        self.LandingLongitude = 0.0
        self.PollPeriod = 5
        self.Counter = 0
        self.CDA = DefaultCDA
        for i in range(self.SlotCount):
            self.Deltas.append(Delta(0,0))


    def GetSlot(self, Altitude):
        Slot = int(Altitude // self.SlotSize)

        if Slot < 0:
            Slot = 0
        if Slot >= self.SlotSize:
            Slot = self.SlotSize-1

        return Slot

    def CalculateAirDensity(self, Altitude):
        if Altitude < 11000.0:
            # below 11Km - Troposphere
            Temperature = 15.04 - (0.00649 * Altitude)
            Pressure = 101.29 * pow((Temperature + 273.1) / 288.08, 5.256)
        elif Altitude < 25000.0:
            # between 11Km and 25Km - lower Stratosphere
            Temperature = -56.46
            Pressure = 22.65 * math.exp(1.73 - ( 0.000157 * Altitude))
        else:
            # above 25Km - upper Stratosphere
            Temperature = -131.21 + (0.00299 * Altitude)
            Pressure = 2.488 * math.pow((Temperature + 273.1) / 216.6, -11.388)

        return Pressure / (0.2869 * (Temperature + 273.1))

    def CalculateDescentRate(self, Weight, CDTimesArea, Altitude):
        Density = self.CalculateAirDensity(Altitude)
	
        return math.sqrt((Weight * 9.81)/(0.5 * Density * CDTimesArea))
            
    def CalculateCDA(self, Weight, Altitude, DescentRate):
        if DescentRate > 0.0:
            Density = self.CalculateAirDensity(Altitude)
	
            # printf("Alt %.0lf, Rate %.1lf, CDA %.1lf\n", Altitude, DescentRate, (Weight * 9.81)/(0.5 * Density * DescentRate * DescentRate));
        
            return (Weight * 9.81)/(0.5 * Density * DescentRate * DescentRate)
        else:
            return self.CDA
            # (lat, long, alt)
    def CalculateLandingPosition(self, Latitude, Longitude, Altitude):
        TimeTillLanding = 0;
	
        Slot = self.GetSlot(Altitude);
        DistanceInSlot = Altitude + 1 - Slot * self.SlotSize
        while Altitude > self.LandingAltitude:
            Slot = self.GetSlot(Altitude)
            if Slot == self.GetSlot(self.LandingAltitude):
                DistanceInSlot = Altitude - self.LandingAltitude
		
            DescentRate = self.CalculateDescentRate(1.0, self.CDA, Altitude)
            
            TimeInSlot = DistanceInSlot / DescentRate
            
            Latitude += self.Deltas[Slot].latitude * TimeInSlot
            Longitude += self.Deltas[Slot].longitude * TimeInSlot
            # printf("SLOT %d: alt %lu, lat=%lf, long=%lf, rate=%lf, dist=%lu, time=%lf\n", Slot, Altitude, Latitude, Longitude, DescentRate, DistanceInSlot, TimeInSlot);
            
            TimeTillLanding = TimeTillLanding + TimeInSlot
            Altitude -= DistanceInSlot
            DistanceInSlot = self.SlotSize
        
        return {'pred_lat': Latitude, 'pred_lon': Longitude ,'TTL': TimeTillLanding}

    def AddGPSPosition(self, Position):
        Result = None
        
        if Position['sats'] >= 4:
            self.Counter = self.Counter + 1
            if self.Counter >= self.PollPeriod:
                self.Counter = 0
                
                if Position['alt'] <= 0:
                    self.AscentRate = 0
                else:
                    self.AscentRate = self.AscentRate * 0.7 + (Position['alt'] - self.PreviousPosition['alt']) * 0.3;

                if (Position['alt'] < self.MinimumAltitude) or (self.MinimumAltitude == 0):
                    self.MinimumAltitude = Position['alt']
                    
                if Position['alt'] > self.MaximumAltitude:
                    self.MaximumAltitude = Position['alt']               

                if (self.AscentRate >= 1.0) and (Position['alt'] > (self.MinimumAltitude+150)) and (self.FlightMode == FlightMode.fmIdle):
                    self.FlightMode = FlightMode.fmLaunched
                    print("*** LAUNCHED ***");
            
                if (self.AscentRate < -10.0) and (self.MaximumAltitude >= (self.MinimumAltitude+2000)) and (self.FlightMode == FlightMode.fmLaunched):
                    self.FlightMode = FlightMode.fmDescending
                    print("*** DESCENDING ***");

                if (self.AscentRate >= -0.1) and (Position['alt'] <= self.LandingAltitude+2000) and (self.FlightMode == FlightMode.fmDescending):
                    self.FlightMode = FlightMode.fmLanded
                    print("*** LANDED ***")
                   
                if self.FlightMode == FlightMode.fmLaunched:
                    # Going up - store deltas
                    
                    Slot = self.GetSlot(Position['alt']/2 + self.PreviousPosition['alt']/2);
                        
                    # Deltas are scaled to be horizontal distance per second (i.e. speed)
                    self.Deltas[Slot].latitude = (Position['lat'] - self.PreviousPosition['lat']) / self.PollPeriod
                    self.Deltas[Slot].longitude = (Position['lon'] - self.PreviousPosition['lon']) / self.PollPeriod
                    
                    print("Slot " + str(Slot) + " = " + str(Position['alt']) + "," + str(self.Deltas[Slot].latitude) + "," + str(self.Deltas[Slot].longitude))
                elif self.FlightMode == FlightMode.fmDescending:
                    # Coming down - try and calculate how well chute is doing

                    self.CDA = (self.CDA * 4 + self.CalculateCDA(1.0, Position['alt']/2 + self.PreviousPosition['alt']/2, (self.PreviousPosition['alt'] - Position['alt']) / self.PollPeriod)) / 5
                
                
                if (self.FlightMode == FlightMode.fmLaunched) or (self.FlightMode == FlightMode.fmDescending):
                    Result = self.CalculateLandingPosition(Position['lat'], Position['lon'], Position['alt']);
                    print(Result)

                    # GPS->PredictedLandingSpeed = CalculateDescentRate(Config.payload_weight, GPS->CDA, Config.LandingAltitude);
				
                    # printf("Expected Descent Rate = %4.1lf (now) %3.1lf (landing), time till landing %d\n", 
                            # CalculateDescentRate(Config.payload_weight, GPS->CDA, GPS->Altitude),
                            # GPS->PredictedLandingSpeed,
                            # GPS->TimeTillLanding);

                    # printf("Current    %f, %f, alt %" PRId32 "\n", GPS->Latitude, GPS->Longitude, GPS->Altitude);
                    # printf("Prediction %f, %f, CDA %lf\n", GPS->PredictedLatitude, GPS->PredictedLongitude, GPS->CDA);


                print('PREDICTOR: ' + str(Position['time']) + ', ' + "{:.5f}".format(Position['lat']) + ', ' + "{:.5f}".format(Position['lon']) + ', ' + str(Position['alt']) + ', ' + str(Position['sats']))

                self.PreviousPosition = Position.copy()
                
        return Result


1 second.       2 seconds.        3 seconds

(0, 0)          (0, 1)            ()

                  v =               v            v 


#Cd = 1.75
predictor = Predictor(40000, 17.5)
# CalculateLandingPosition(Latitude, Longitude, Altitude)
lat = 35.0 #current latitude
longi = -117.15
alt = 60000
time = 0
for i in range(1, 30):
  d = {'time': str(time) + str(i), 'lat': lat, 'lon': longi, 'alt': alt, 'sats': 5, 'fixtype': 0}
  lat += 1
  longi += 1
  alt += 100 #increasing altitude means ascending
  print(predictor.AddGPSPosition(d))

# payload is currently at (0, 0, 10000 feet) 0 seconds --> cant calculate the landing position 
# payload is currently at (0, 1, 9000 feet) 2 seconds --> can calculate the landing position (10, 20, 0 ft)
# payload is currently at (0, 2, 8000 feet) 4 seconds --> can calculate the landing position (11.1, 20, 0 ft)


#currently at (0, 0, 10000 ft) --> landing prediction (0, 0, 0 ft) --> fell straight down 

for i in range(31, 60):
  d = {'time': str(time) + str(i), 'lat': lat, 'lon': longi, 'alt': alt, 'sats': 5, 'fixtype': 0}
  lat += 1
  longi += 1
  alt -= 100
  print(predictor.AddGPSPosition(d))
# Currently at 35, -117.15
# 36, -116.15

import math

#Constants
Weight = 2.72 # [kg]
initial_descent_rate = 4.56 # [m/s], given by Rocketman Parachutes
g = 9.18
SlotSize = 100
SlotCount = 60000
Deltas = []
for i in range(SlotCount):
    Deltas.append(Delta(0,0))
LandingAltitude = 609.6 #[meters]


#Variables
Altitude = 30490 # [meters], current altitude of the balloon
Latitude = 35.04
Longitude = -117.15

#calculate the density of air at any altitude, altitude is in meters
def CalculateAirDensity(Altitude):
        if Altitude < 11000.0: # below 11Km - Troposphere
            Temperature = 15.04 - (0.00649 * Altitude)
            Pressure = 101.29 * pow((Temperature + 273.1) / 288.08, 5.256)
        
        elif Altitude < 25000.0: # between 11Km and 25Km - lower Stratosphere
            Temperature = -56.46
            Pressure = 22.65 * math.exp(1.73 - ( 0.000157 * Altitude))
        
        else: # above 25Km - upper Stratosphere
            Temperature = -131.21 + (0.00299 * Altitude)
            Pressure = 2.488 * math.pow((Temperature + 273.1) / 216.6, -11.388)

        return Pressure / (0.2869 * (Temperature + 273.1)) #air pressure

#calculate the drag coefficient times area
def CalculateCDA(Weight, Altitude, initial_descent_rate):
        Density = CalculateAirDensity(Altitude)

        CDA = (2 * Weight) / (initial_descent_rate * initial_descent_rate * Density)

        return CDA 

#calculate the descent rate at a specific altitude
def CalculateDescentRate(Weight, Altitude):
        Density = CalculateAirDensity(Altitude)
        CDTimesArea = CalculateCDA(Weight, Altitude, initial_descent_rate)
	
        return math.sqrt((2* Weight * g)/(Density * CDTimesArea)) #descent rate [m/s]

#not really sure what this does
def GetSlot(Altitude):
        Slot = int(Altitude // SlotSize)

        if Slot < 0:
            Slot = 0
        if Slot >= SlotSize:
            Slot = SlotSize-1

        return Slot

#calculate the landing position
def CalculateLandingPosition(Latitude, Longitude, Altitude):
        TimeTillLanding = 0;
	
        Slot = GetSlot(Altitude);
        DistanceInSlot = Altitude + 1 - Slot * SlotSize
	
        while Altitude > LandingAltitude:
            Slot = GetSlot(Altitude)
		
            if Slot == GetSlot(LandingAltitude):
                DistanceInSlot = Altitude - LandingAltitude
		
            DescentRate = CalculateDescentRate(Weight, Altitude)
            
            TimeInSlot = DistanceInSlot / DescentRate
            
            Latitude += Deltas[Slot].latitude * TimeInSlot
            Longitude += Deltas[Slot].longitude * TimeInSlot
            
            # printf("SLOT %d: alt %lu, lat=%lf, long=%lf, rate=%lf, dist=%lu, time=%lf\n", Slot, Altitude, Latitude, Longitude, DescentRate, DistanceInSlot, TimeInSlot);
            
            TimeTillLanding = TimeTillLanding + TimeInSlot
            Altitude -= DistanceInSlot
            DistanceInSlot = SlotSize
                    
        return {'pred_latitude': Latitude, 'pred_longitude': Longitude ,'time_till_landing': TimeTillLanding}

#constants
g = 9.18 #[m/s^2]
landing_alt = 2000 #[meters]
descent_rate = 4.56 # [m/s], not really constant but we will estimate it to be

#variables
curr_alt = 30480 #[meters], current altitude of the balloon
curr_lat = 35.04 #current latitude of the balloon
curr_long = -117.15 #current longitude of the balloon

#calculate the time to descent in the z direction, v=dx/dt -> dt=dx/v
descent_time = (curr_alt - landing_alt) / descent_rate

#calculate the intial velocity in the x and y direction
#v_x = difference in latitude/difference in time, between the last two packets
#v_y = difference in longitude/difference in time, between the last two packets
#just use arbitrary values for now
v_x = 2 #[m/s]
v_y = 2 #[m/s]

#calculate the landing position, x=x0+v0t+1/2at^2
pred_x = curr_lat + v_x * descent_time 
pred_y = curr_long + v_y * descent_time

print("Predicting latitude: ", pred_x, "Predicting longitude: ", pred_y , "Time to descent: ", descent_time)