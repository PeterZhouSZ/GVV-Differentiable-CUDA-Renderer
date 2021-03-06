
import tensorflow as tf
import utils.OBJReader as ObjReader

########################################################################################################################
# Isometry Loss
########################################################################################################################

class IsometryLoss:

    ########################################################################################################################

    def __init__(self, meshFilePath, restTensor):

        # obj Reader
        self.objReader = ObjReader.OBJReader(meshFilePath)

        # adjacency
        self.adjacency = tf.constant(self.objReader.adjacency, dtype=tf.float32)
        self.adjacency = tf.reshape(self.adjacency, [self.objReader.numberOfVertices, self.objReader.numberOfVertices, 1])
        self.adjacency = tf.tile(self.adjacency, [1, 1, 3])

        # weight adjacency
        self.weightAdjacency = tf.constant(self.objReader.adjacencyWeights, dtype=tf.float32)

        # rest vertex pos
        self.restVertexPos = restTensor

        #rest edge length
        self.restEdgeLength = self.get_edge_length(self.restVertexPos)

    ########################################################################################################################

    def get_edge_length(self, vertexPos):

        vertexPosI = tf.reshape(vertexPos,[-1, self.objReader.numberOfVertices, 1, 3])
        vertexPosI = tf.tile(vertexPosI, [1, 1, self.objReader.numberOfVertices, 1])
        vertexPosI = self.adjacency * vertexPosI

        vertexPosJ = tf.reshape(vertexPos, [-1, 1, self.objReader.numberOfVertices, 3])
        vertexPosJ = tf.tile(vertexPosJ, [1, self.objReader.numberOfVertices,1, 1])
        vertexPosJ = self.adjacency * vertexPosJ

        edgeLength = vertexPosI - vertexPosJ
        edgeLength = edgeLength  * edgeLength
        edgeLength = tf.reduce_sum(edgeLength, 3)
        edgeLength = tf.sqrt(edgeLength)

        return edgeLength

    ########################################################################################################################

    def getLoss(self, inputMeshTensor):
        batchSize = tf.shape(inputMeshTensor)[0]

        restEdgeLength = tf.tile(self.restEdgeLength, [batchSize, 1,1])

        edgeLength = self.get_edge_length(inputMeshTensor)

        diff = restEdgeLength - edgeLength

        loss =tf.reduce_sum(
                            tf.reduce_sum((diff * diff), 0) #* self.weightAdjacency todo
                           )

        loss = loss / float(batchSize * self.objReader.numberOfEdges)

        return loss

    ########################################################################################################################
