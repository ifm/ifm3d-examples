/*
 * Copyright (C) 2018 ifm electronic, gmbh
 *
 *
 * Licensed under the Apache License, Version 2.0 (the "License");
 * you may not use this file except in compliance with the License.
 * You may obtain a copy of the License at
 *
 * http://www.apache.org/licenses/LICENSE-2.0
 *
 * Unless required by applicable law or agreed to in writing, software
 * distributed under the License is distribted on an "AS IS" BASIS,
 * WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
 * See the License for the specific language governing permissions and
 * limitations under the License.
 */
 //
 // ex-simpleimage_ppm_io.cpp
 //
 // This example shows how to get the images from ifm3dlib without opencv and PCL dependency
 // and how to write the ppm images with the data from device. This example scales the data
 // from camera to unsigned char for storing in the ppm file.  For Scaling Distance data 
 // Maximum distance is considered as 2.5m or 2500mm whereas for amplitude data min and max values are calculated 
 // from data (auto scaling)  

#include <iostream>
#include <limits.h>
#include <memory>
#include <string>
#include <thinks/ppm.hpp>
#include <ifm3d/camera.h>
#include <ifm3d/fg.h>
#include <ifm3d/simpleimage.h>



using namespace std;



bool writePPMFile(ifm3d::SimpleImageBuffer::Img &img, std::string const& filename)
{
	auto const write_width = (size_t)img.width;
	auto const write_height = (size_t)img.height;
	auto write_pixels = vector<uint8_t>(write_width * write_height * 3); // 3 for RGB channels 
	auto pixel_index = size_t{ 0 };
	for (auto col = size_t{ 0 }; col < write_height; ++col) {
		for (auto row = size_t{ 0 }; row < write_width; ++row) {
			write_pixels[pixel_index * 3 + 0] = static_cast<uint8_t>(*(img.data.data() + pixel_index));
			write_pixels[pixel_index * 3 + 1] = static_cast<uint8_t>(*(img.data.data() + pixel_index));
			write_pixels[pixel_index * 3 + 2] = static_cast<uint8_t>(*(img.data.data() + pixel_index));
			++pixel_index;
		}
	}
	try
	{
		thinks::ppm::writeRgbImage(filename, write_width, write_height, write_pixels);
	}
	catch (exception e)
	{
		std::cerr << e.what();
		return false;
	}
	return true;
}
// scales the data with min max values 
template <typename  T>
void scaleImageToRGB(ifm3d::SimpleImageBuffer::Img &input, ifm3d::SimpleImageBuffer::Img &confidence, ifm3d::SimpleImageBuffer::Img &output, double min = 0.0f, double max = 0.0f)
{
	output.width = input.width;
	output.height = input.height;
	output.format = ifm3d::pixel_format::FORMAT_8U;
	output.data.resize(output.width*output.height);

	float scalingFactor = 255.0 / ((max - min) != 0 ? (max - min) : 1);

	for (int index = 0; index < input.width * input.height; index++)
	{
		T value = *((T*)(input.data.data()) + index);
		if ((*(confidence.data.data() + index) & 0x01) == 0x00) // checking valid pixel 
			*(output.data.data() + index) = (uint8_t)((value - min)* scalingFactor);
		else
		{
			*(output.data.data() + index) = 0; // All invalid pixels 
		}
	}
}

// find the min max of the data
template < typename  T >
void findMinAndMax(ifm3d::SimpleImageBuffer::Img &input, ifm3d::SimpleImageBuffer::Img &confidence, double &min, double &max)
{
	max = 0;
	min = (double)INT_MAX;
	for (int index = 0; index < input.width * input.height; index++)
	{
		T value = *((T*)(input.data.data()) + index);
		if ((*(confidence.data.data() + index) & 0x01) == 0x00)
		{
			min = std::min((T)min, value);
		}
		if ((*(confidence.data.data() + index) & 0x01) == 0x00)
		{
			max = std::max((T)max, value);
		}
	}
}

int main(int argc, const char **argv)
{
	auto cam = ifm3d::Camera::MakeShared();

	ifm3d::SimpleImageBuffer::Ptr img = std::make_shared<ifm3d::SimpleImageBuffer>();
	ifm3d::FrameGrabber::Ptr fg =
		std::make_shared<ifm3d::FrameGrabber>(
			cam, ifm3d::IMG_AMP | ifm3d::IMG_CART | ifm3d::IMG_RDIS);

	if (!fg->WaitForFrame(img.get(), 1000))
	{
		std::cerr << "Timeout waiting for camera!" << std::endl;
		return -1;
	}
	// acquiring data from the device 
	ifm3d::SimpleImageBuffer::Img confidence = img->ConfidenceImage();
	ifm3d::SimpleImageBuffer::Img amplitude = img->AmplitudeImage();
	ifm3d::SimpleImageBuffer::Img distance = img->DistanceImage();

	// for storing scaled output 
	ifm3d::SimpleImageBuffer::Img distance_scaled;
	ifm3d::SimpleImageBuffer::Img amplitude_scaled;

	double min = 0.0;
	double max = 0.0;
	// max and mindistance for scaling distance image uint8 format 
	auto const max_distance = 2.5;
	auto const min_distance = 0.0;
	// for 32F data  O3X camera
	if (distance.format == ifm3d::pixel_format::FORMAT_32F)
	{
		scaleImageToRGB<float>(distance, confidence, distance_scaled, min_distance, max_distance);
		findMinAndMax<float>(amplitude, confidence, min, max);
		scaleImageToRGB<float>(amplitude, confidence, amplitude_scaled, min, max);
	}
	//for 16u data  O3D camera
	else if(distance.format == ifm3d::pixel_format::FORMAT_16U)
	{	  //if data format is 16U then distances are in millimeters, Hence max distance is multiplied by 1000. 
		scaleImageToRGB<unsigned short>(distance, confidence, distance_scaled, min_distance, max_distance * 1000);
		findMinAndMax<unsigned short>(amplitude, confidence, min, max);
		scaleImageToRGB<unsigned short>(amplitude, confidence, amplitude_scaled, min, max);
	}
	else
	{
		std::cerr << "Unknown Format" << std::endl;
	}

	//writing images too ppm format 
	if (!writePPMFile(distance_scaled, "distanceImage.ppm"))
	{
		std::cerr << "Not able to write the distance data in ppm format" << std::endl;
		return -1;
	}

	if (!writePPMFile(amplitude_scaled, "amplitudeImage.ppm"))
	{
		std::cerr << "Not able to write the amplitude data in ppm format" << std::endl;
		return -1;
	}

	std::cout << "Done with simpleimage ppmio example" << std::endl;
	return 0;
}
