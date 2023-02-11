# Solutions

The problem is about validating whether a given coordinate is a fish farm or not, if yes, then count how many ponds and the area of the pond.

First thing first that one must have is data from satellite imagery to get a picture of the location from the latitude and longitude. Once one has a clear image of the location, we can perform object detection to compute the number of ponds in the location. Then, we can use object segmentation to grasp the bounding boxes of each pond and calculate the distance and the area of the pond.

Collecting high-quality satellite imagery is challenging for this test because open access data only provide a low resolution such as sentinel or Landsat as shown in the picture below.

![Jawa -7.675039, 107.769191](https://raw.githubusercontent.com/andreaschandra/fishpond-validator/main/data/image_arrays/jawa_-7.675039_107.769191_0.jpg)
![Jawa -7.786883, 108.155444](https://raw.githubusercontent.com/andreaschandra/fishpond-validator/main/data/image_arrays/jawa_-7.786883_108.155444_1.jpg)
![Sulawesi -5.552498, 120.375194](https://raw.githubusercontent.com/andreaschandra/fishpond-validator/main/data/image_arrays/sulawesi_-5.552498_120.375194_2.jpg)
![Sulawesi -5.559804, 120.376871](https://raw.githubusercontent.com/andreaschandra/fishpond-validator/main/data/image_arrays/sulawesi_-5.559804_120.376871_3.jpg)
![Sulawesi -5.573898, 120.384974](https://raw.githubusercontent.com/andreaschandra/fishpond-validator/main/data/image_arrays/sulawesi_-5.573898_120.384974_4.jpg)

Even worse, Sulawesi ones are not available in the collections.
Therefore, enterprise access is needed to collect the data and perform the detection and segmentation.