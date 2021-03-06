
########################################################################################################################
# Imports
########################################################################################################################

import tensorflow as tf
from sys import platform
import data.test_mesh_tensor as test_mesh_tensor
import data.test_SH_tensor as test_SH_tensor
import CudaRenderer
import utils.CheckGPU as CheckGPU
import cv2 as cv
import numpy as np
import utils.OBJReader as OBJReader
import utils.CameraReader as CameraReader

########################################################################################################################
# Load custom operators
########################################################################################################################

RENDER_OPERATORS_PATH = ""
if platform == "linux" or platform == "linux2":
    RENDER_OPERATORS_PATH = "../cpp/binaries/Linux/Release/libCustomTensorFlowOperators.so"
elif platform == "win32" or platform == "win64":
    RENDER_OPERATORS_PATH = "../cpp/binaries/Win64/Release/CustomTensorFlowOperators.dll"
customOperators = tf.load_op_library(RENDER_OPERATORS_PATH)

########################################################################################################################
# CudaRendererGpu class
########################################################################################################################

numberOfBatches = 1
renderResolutionU = 1024
renderResolutionV = 1024
imageFilterSize = 1
textureFilterSize = 1

cameraReader = CameraReader.CameraReader('data/cameras.calibration',renderResolutionU,renderResolutionV)
objreader = OBJReader.OBJReader('data/magdalena.obj')

inputVertexPositions = test_mesh_tensor.getGTMesh()
inputVertexPositions = np.asarray(inputVertexPositions)
inputVertexPositions = inputVertexPositions.reshape([1, objreader.numberOfVertices, 3])
inputVertexPositions = np.tile(inputVertexPositions, (numberOfBatches, 1, 1))

inputVertexColors = objreader.vertexColors
inputVertexColors = np.asarray(inputVertexColors)
inputVertexColors = inputVertexColors.reshape([1, objreader.numberOfVertices, 3])
inputVertexColors = np.tile(inputVertexColors, (numberOfBatches, 1, 1))

inputTexture = objreader.textureMap
inputTexture = np.asarray(inputTexture)
inputTexture = inputTexture.reshape([1, objreader.texHeight, objreader.texWidth, 3])
inputTexture = np.tile(inputTexture, (numberOfBatches, 1, 1, 1))

inputSHCoeff = test_SH_tensor.getSHCoeff(numberOfBatches, cameraReader.numberOfCameras)

########################################################################################################################
# Test color function
########################################################################################################################

def test_color_gradient():

    VertexPosConst = tf.constant(inputVertexPositions, dtype=tf.float32)
    VertexColorConst = tf.constant(inputVertexColors, dtype=tf.float32)
    VertexTextureConst = tf.constant(inputTexture, dtype=tf.float32)
    SHCConst = tf.constant(inputSHCoeff, dtype=tf.float32)

    rendererTarget = CudaRenderer.CudaRendererGpu(
                                        faces_attr                   = objreader.facesVertexId,
                                        texCoords_attr               = objreader.textureCoordinates,
                                        numberOfVertices_attr        = len(objreader.vertexCoordinates),
                                        renderResolutionU_attr       = renderResolutionU,
                                        renderResolutionV_attr       = renderResolutionV,
                                        albedoMode_attr              = 'textured',
                                        shadingMode_attr             = 'shadeless',
                                        image_filter_size_attr       = imageFilterSize,
                                        texture_filter_size_attr     = textureFilterSize,
                                        numberOfCameras_attr=1,
                                        vertexPos_input              = VertexPosConst,
                                        vertexColor_input            = VertexColorConst,
                                        texture_input                = VertexTextureConst,
                                        shCoeff_input                = SHCConst,
                                        targetImage_input            = tf.zeros([numberOfBatches, cameraReader.numberOfCameras, renderResolutionV, renderResolutionU, 3]),
                                        extrinsics_input=[cameraReader.extrinsics, cameraReader.extrinsics, cameraReader.extrinsics],
                                        intrinsics_input=[cameraReader.intrinsics, cameraReader.intrinsics, cameraReader.intrinsics],
                                        nodeName='target'
                                        )

    target = rendererTarget.getRenderBufferTF()

    VertexTextureRand = tf.Variable(tf.ones(VertexTextureConst.shape))

    opt = tf.keras.optimizers.SGD(learning_rate=100.0)

    for i in range(3000):

        with tf.GradientTape() as tape:
            tape.watch(VertexTextureRand)
            renderer = CudaRenderer.CudaRendererGpu(
                faces_attr=objreader.facesVertexId,
                texCoords_attr=objreader.textureCoordinates,
                numberOfVertices_attr=len(objreader.vertexCoordinates),
                renderResolutionU_attr=renderResolutionU,
                renderResolutionV_attr=renderResolutionV,
                numberOfCameras_attr =1,
                albedoMode_attr='textured',
                shadingMode_attr='shadeless',
                image_filter_size_attr=imageFilterSize,
                texture_filter_size_attr=textureFilterSize,

                vertexPos_input=VertexPosConst,
                vertexColor_input=VertexColorConst,
                texture_input=VertexTextureRand,
                shCoeff_input=SHCConst,
                targetImage_input =target,
                extrinsics_input = [cameraReader.extrinsics, cameraReader.extrinsics, cameraReader.extrinsics],
                intrinsics_input = [cameraReader.intrinsics, cameraReader.intrinsics, cameraReader.intrinsics],
                nodeName = 'render'
            )

            output = renderer.getRenderBufferTF()

            Loss1 = (output-target) * (output-target)
            Loss = tf.reduce_sum(Loss1) / (float(cameraReader.numberOfCameras) * float(objreader.numberOfVertices))

        #apply gradient
        Color_Grad = tape.gradient(Loss,VertexTextureRand)
        opt.apply_gradients(zip([Color_Grad],[VertexTextureRand]))

        # print loss
        print(i, Loss.numpy())

        # output images
        outputCV = renderer.getRenderBufferOpenCV(0, 0)
        targetCV = rendererTarget.getRenderBufferOpenCV(0, 0)

        combined = targetCV
        cv.addWeighted(outputCV, 1.0, targetCV, 0.0, 0.0, combined)
        cv.imshow('combined', combined)
        textureCV = cv.cvtColor(VertexTextureRand[0,:,:,:].numpy(), cv.COLOR_RGB2BGR)
        cv.imshow('texture', textureCV)
        cv.waitKey(1)

    cv.imwrite('D:/texture.png', textureCV * 255.0)

########################################################################################################################
# main
########################################################################################################################

freeGPU = CheckGPU.get_free_gpu()

if freeGPU:
    test_color_gradient()   
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    
    