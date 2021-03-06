#!/usr/bin/env python3
# -*- coding: utf-8 -*
# sample_python aims to allow seamless integration with lua.
# see examples below

import os
import sys
import pdb  # use pdb.set_trace() for debugging
import code # or use code.interact(local=dict(globals(), **locals()))  for debugging.
import xml.etree.ElementTree as ET
import numpy as np
from PIL import Image

def normalize(vector):
    size = np.sqrt(np.sum(vector**2))
    return vector / size

class Color:
    def __init__(self, R, G, B):
        self.color=np.array([R,G,B]).astype(np.float)

    # Gamma corrects this color.
    # @param gamma the gamma value to use (2.2 is generally used).
    def gammaCorrect(self, gamma):
        inverseGamma = 1.0 / gamma;
        self.color=np.power(self.color, inverseGamma)

    def toUINT8(self):
        return (np.clip(self.color, 0,1)*255).astype(np.uint8)

class Camera:
    def __init__(self, viewPoint, direction, up, projDist, viewWidth, viewHeight, imgSize):
        self.viewPoint = viewPoint
        self.direction = normalize(-direction)
        self.u = normalize(np.cross(up, self.direction))
        self.v = normalize(np.cross(self.direction, self.u))

        self.viewDist = projDist
        self.viewWidth = viewWidth
        self.viewHeight = viewHeight
        self.imgWidth = imgSize[0]
        self.imgHeight = imgSize[1]

    def getRay(self, i, j):
        uc = j - self.imgWidth / 2
        vc = -i + self.imgHeight / 2
        wc = (self.viewDist / self.viewWidth) * self.imgWidth
        s = self.viewPoint + self.u * uc + self.v * vc - self.direction * wc
        return self.viewPoint, s - self.viewPoint

class Sphere:
    def __init__(self, center, radius, shader):
        self.center = center
        self.radius = radius
        self.shader = shader

    # returns t, hitPoint, hitNormal
    def intersect(self, rayPoint, rayVec):
        hitPoint = np.array([0., 0., 0.])
        hitNormal = np.array([0., 0., 0.])
        b = np.dot(rayPoint - self.center, rayVec)
        c = np.dot(rayPoint - self.center, rayPoint - self.center) - self.radius * self.radius
        insideRoot = b * b - c
        if insideRoot < 0:
            return np.inf, hitPoint, hitNormal
        else:
            t1 = -b - np.sqrt(insideRoot)
            t2 = -b + np.sqrt(insideRoot)
            # return t1 if t1 * t1 < t2 * t2 else t2
            if t1 * t1 < t2 * t2:
                t = t1
                hitPoint = rayPoint + t * rayVec
                hitNormal = hitPoint - self.center
            else:
                t = t2
                hitPoint = rayPoint + t * rayVec
                hitNormal = hitPoint - self.center
            return t, hitPoint, hitNormal

class Box:
    def __init__(self, minPt, maxPt, shader):
        self.minPt = minPt
        self.maxPt = maxPt
        self.shader = shader

    def intersect(self, rayPoint, rayVec):
        rayVec = normalize(rayVec)

        tx0, tx1, ty0, ty1, tz0, tz1 = np.inf, np.inf, np.inf, np.inf, np.inf, np.inf
        vx, vy, vz = -1, -1, -1

        if rayVec[0] != 0:
            tx0 = (self.minPt[0] - rayPoint[0]) / rayVec[0]
            tx1 = (self.maxPt[0] - rayPoint[0]) / rayVec[0]
        if rayVec[1] != 0:
            ty0 = (self.minPt[1] - rayPoint[1]) / rayVec[1]
            ty1 = (self.maxPt[1] - rayPoint[1]) / rayVec[1]
        if rayVec[2] != 0:
            ty0 = (self.minPt[2] - rayPoint[2]) / rayVec[2]
            ty1 = (self.maxPt[2] - rayPoint[2]) / rayVec[2]
        
        if tx0 > tx1:
            tmp = tx0
            tx0 = tx1
            tx1 = tmp
            vx = 1
        if ty0 > ty1:
            tmp = ty0
            ty0 = ty1
            ty1 = tmp
            vy = 1
        if tz0 > tz1:
            tmp = tz0
            tz0 = tz1
            tz1 = tmp
            vz = 1

        tminarr = np.array([tx0, ty0, tz0])
        tminidx = 0
        if ty0 > tminarr[tminidx]:
            tminidx = 1
        if tz0 > tminarr[tminidx]:
            tminidx = 2
        
        tmaxarr = np.array([tx1, ty1, tz1])
        tmaxidx = 0
        if ty1 > tmaxarr[tmaxidx]:
            tmaxidx = 1
        if tz1 > tmaxarr[tmaxidx]:
            tmaxidx = 2

        t0 = np.inf
        hitPoint = np.array([0, 0, 0])
        hitNormal = np.array([0, 0, 0])
        if tmaxarr[tmaxidx] > tminarr[tminidx]:
            t0 = tminarr[tminidx]
            if tminidx == 0:
                normal = np.array([vx, 0, 0])
            elif tminidx == 1:
                normal = np.array([0, vy, 0])
            elif tminidx == 2:
                normal = np.array([0, 0, vz])
            hitPoint = rayPoint + t0 * rayVec
            hitNormal = normal
        if t0 < 0:
            t0 = np.inf
        return t0, hitPoint, hitNormal


class Shader:
    def __init__(self, diffuseColor, specularColor = np.array([0., 0., 0.]), exponent = 50):
        self.diffuseColor = diffuseColor
        self.specularColor = specularColor
        self.exponent = exponent

class Light:
    def __init__(self, position, intensity):
        self.position = position
        self.intensity = intensity

def checkIntersect(rayPoint, rayVec, objSphereList, objBoxList):
    tmin = np.inf
    hitPoint = np.array([0., 0., 0.])
    hitNormal = np.array([0., 0., 0.])

    for object in objSphereList:
        t, hp, hn = object.intersect(rayPoint, rayVec)
        if t < tmin:
            tmin = t
            hitPoint = hp
            hitNormal = hn
            hitObject=object
            
    for object in objBoxList:
        t, hp, hn = object.intersect(rayPoint, rayVec)
        if t < tmin:
            tmin = t
            hitPoint = hp
            hitNormal = hn
            hitObject=object

    if tmin == np.inf:
        hitObject = -1
    return tmin, hitPoint, hitNormal, hitObject

def parseInput():

    tree = ET.parse(sys.argv[1])
    root = tree.getroot()

    objSphereList=[]
    objBoxList=[]
    lightList=[]  
    shaderDictionary={} 

    # set default values
    viewDir=np.array([0,0,-1]).astype(np.float)
    viewUp=np.array([0,1,0]).astype(np.float)
    viewProjNormal=-1*viewDir  # you can safely assume this. (no examples will use shifted perspective camera)
    viewWidth=1.0
    viewHeight=1.0
    projDistance=1.0
    intensity=np.array([1,1,1]).astype(np.float)  # how bright the light is.

    imgSize=np.array(root.findtext('image').split()).astype(np.int)

    # set the camera option
    for c in root.findall('camera'):
        if c.find('viewPoint') != None:
            viewPoint=np.array(c.findtext('viewPoint').split()).astype(np.float)
        if c.find('viewDir') != None:
            viewDir=np.array(c.findtext('viewDir').split()).astype(np.float)
        if c.find('viewUp') != None:
            viewUp=np.array(c.findtext('viewUp').split()).astype(np.float)
        if c.find('viewNormal') != None:
            projNormal=np.array(c.findtext('projNormal').split()).astype(np.float)
        if c.find('projDistance') != None:
            projDistance=float(c.findtext('projDistance'))
        if c.find('viewWidth') != None:
            viewWidth=float(c.findtext('viewWidth'))
        if c.find('viewHeight') != None:
            viewHeight=float(c.findtext('viewHeight'))
        camera = Camera(viewPoint, viewDir, viewUp, projDistance, viewWidth, viewHeight, imgSize)

    # get the shader
    for c in root.findall('shader'):
        diffuseColor=np.array(c.findtext('diffuseColor').split()).astype(np.float)
        if c.get('type')=='Lambertian':
            shaderDictionary[c.get('name')]=Shader(diffuseColor)
        elif c.get('type')=='Phong':
            specularColor=np.array(c.findtext('specularColor').split()).astype(np.float)
            exponent=np.array(c.findtext('exponent').split()).astype(np.float)
            shaderDictionary[c.get('name')]=Shader(diffuseColor, specularColor, exponent)  

    # get the Object surface
    for c in root.findall('surface'):
        objShaderTag=c.find('shader')
        objShaderName=objShaderTag.get('ref')
        objShader=shaderDictionary[objShaderName]

        if c.get('type')=='Sphere':
            objCenter=np.array(c.findtext('center').split()).astype(np.float)
            objRadius=np.array(c.findtext('radius').split()).astype(np.float)
            tmpObj=Sphere(objCenter, objRadius, objShader)
            objSphereList += [tmpObj]

        if c.get('type')=='Box':
            objMinPt=np.array(c.findtext('minPt').split()).astype(np.float)
            objMaxPt=np.array(c.findtext('maxPt').split()).astype(np.float)
            tmpObj=Box(objMinPt, objMaxPt, objShader)
            objBoxList += [tmpObj]

    # get the light
    for c in root.findall('light'):
        lightPosition=np.array(c.findtext('position').split()).astype(np.float)
        lightIntensity=np.array(c.findtext('intensity').split()).astype(np.float)
        tmpLight=Light(lightPosition, lightIntensity)
        lightList+= [tmpLight]

    return camera, objSphereList, objBoxList, imgSize, lightList

def main():

    # parse input file
    camera, objSphereList, objBoxList, imgSize, lightList = parseInput()

    # Create an empty image
    channels=3
    img = np.zeros((imgSize[1], imgSize[0], channels), dtype=np.uint8)
    img[:,:]=0
    
    # make image
    for i in np.arange(imgSize[1]):
        for j in np.arange(imgSize[0]):
            imgColor = np.array([0, 0, 0])
            # get ray
            rayPoint, rayVec = camera.getRay(i, j)
            # find intersect
            tmin, hitPoint, hitNormal, hitObject = checkIntersect(rayPoint, rayVec, objSphereList, objBoxList)
            # case: there is intersection
            if tmin < np.inf:
                # handle shadows
                imgColor = np.array([0., 0., 0.])
                normal = normalize(hitNormal)
                V = normalize(-rayVec)
                for light in lightList:
                    # Lambertian
                    lightVec = normalize(light.position - hitPoint)
                    # Phong
                    h = normalize(lightVec + V)
                    t_shadow, hp_s, hn_s, obj_s = checkIntersect(hitPoint, lightVec, objSphereList, objBoxList)
                    if t_shadow == np.inf:
                        imgColor += hitObject.shader.diffuseColor * light.intensity * max([0, lightVec@normal])
                        imgColor += hitObject.shader.specularColor * light.intensity * (max([0, h@normal])**hitObject.shader.exponent)
            imgColor = 255 * imgColor
            for idx in range(3):
                if(imgColor[idx] > 255):
                    imgColor[idx] = 255
            img[i][j] = imgColor

    rawimg = Image.fromarray(img, 'RGB')
    #rawimg.save('out.png')
    #rawimg.save(sys.argv[1]+'.png')
    rawimg.save(sys.argv[1] + '_test.png')
    
if __name__=="__main__":
    main()
