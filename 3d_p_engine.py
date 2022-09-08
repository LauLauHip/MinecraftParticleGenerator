import pygame as pg
from OpenGL.GL import *
import numpy as np
import ctypes
import pyrr
from OpenGL.GL.shaders import compileProgram, compileShader
from PIL import Image

texture = 'Combined.png'
tex = Image.open(texture)
tex = tex.transpose(Image.FLIP_TOP_BOTTOM)
xSize, ySize = tex.size

xyz = []
st = []

class App:

    def __init__(self):
        #init python
        pg.init()
        self.screen = pg.display.set_mode((1280, 960), pg.OPENGL|pg.DOUBLEBUF)
        Icon = pg.image.load(texture)
        pg.display.set_icon(Icon)
        pg.display.set_caption('3D Preview')
        self.clock = pg.time.Clock()
        #init opengl
        glClearColor(0.2, 0.21, 0.25, 1)
        glEnable(GL_DEPTH_TEST)
        self.shader = self.createShader('vertex.txt', 'fragment.txt')
        glUseProgram(self.shader)
        glUniform1i(glGetUniformLocation(self.shader, "imageTexture"), 0)
        #rendering menu
        self.button_1 = pg.Rect(100, 100, 100, 100)
        #rendering opengl
        self.transform = Transform(position=[0, 0, -2.7], eulers=[0, 0, 0])
        self.cube_mesh = Mesh('Alug_MCPre.obj')
        self.texture = Material(texture)
        self.generate_holo()
        projection_transform = pyrr.matrix44.create_perspective_projection(
            fovy = 45, aspect = 1280/960, near = 0.1, far = 10, dtype=np.float32
            )
        glUniformMatrix4fv(
            glGetUniformLocation(self.shader, "projection"),
            1, GL_FALSE, projection_transform
            )
        self.modelMatrixLocation = glGetUniformLocation(self.shader, "model")
        self.mainLoop()
        
    def createShader(self, vertexFilepath, fragmentFilepath):
        with open(vertexFilepath, 'r') as f:
            vertex_src = f.readlines()
        with open(fragmentFilepath, 'r') as f:
            fragment_src = f.readlines()
        shader = compileProgram(
            compileShader(vertex_src, GL_VERTEX_SHADER),
            compileShader(fragment_src, GL_FRAGMENT_SHADER)
            )
        return shader
    
    def mainLoop(self):
        running = True
        while (running):
            for event in pg.event.get():
                if event.type == pg.QUIT:
                    running = False
            
            self.transform.eulers[2] += 0.2
            if self.transform.eulers[2] > 360:
                self.transform.eulers[2] -= 360
            
            #refreshing
            glClear(GL_COLOR_BUFFER_BIT|GL_DEPTH_BUFFER_BIT)
            glUseProgram(self.shader)
            self.texture.use()
            
            model_transform = pyrr.matrix44.create_identity(dtype=np.float32)
            model_transform = pyrr.matrix44.multiply(
                m1=model_transform,
                m2=pyrr.matrix44.create_from_eulers(
                    eulers=np.radians(self.transform.eulers),
                    dtype = np.float32
                    )
                )
            model_transform = pyrr.matrix44.multiply(
                m1=model_transform,
                m2=pyrr.matrix44.create_from_translation(
                    vec=self.transform.position,
                    dtype = np.float32
                    )
                )
            glUniformMatrix4fv(self.modelMatrixLocation, 1, GL_FALSE, model_transform)
            glBindVertexArray(self.cube_mesh.vao)
            glDrawArrays(GL_TRIANGLES, 0, self.cube_mesh.vertex_count)
            pg.display.flip()
            self.clock.tick(60)
        self.quit()
    
    def generate_holo(self):
        with open('out.mcfunction', 'w') as f:
            if len(xyz) == len(st):
                space = ' ~'
                multipl = 0.1
                size = 0.1
                cmds = ''
                print(len(xyz))
                for i in range(len(xyz)):
                    x = st[i][0] - 1
                    y = st[i][1] - 1
                    cmds += 'particle dust ' + str(tex.getpixel((x, y))[0] / 255) + ' ' + str(tex.getpixel((x, y))[1] / 255) + ' ' + str(tex.getpixel((x, y))[2] / 255) + f' {size}' + space + str(xyz[i][0]*multipl) + space + str(xyz[i][1]*multipl) + space + str(xyz[i][2]*multipl) + ' 0 0 0 0 1 force\n'
                f.write(cmds)
    
    def quit(self):
        self.cube_mesh.destroy()
        self.texture.destroy()
        glDeleteProgram(self.shader)
        pg.quit()

class Transform:
    def __init__(self, position, eulers):
        self.position = np.array(position, dtype=np.float32)
        self.eulers = np.array(eulers, dtype=np.float32)

class Mesh:
    def __init__(self, filepath):
        self.vertices = self.loadMesh(filepath)
        self.vertices = np.array(self.vertices, dtype=np.float32)
        self.vertex_count = len(self.vertices) // 8
        
        self.vao = glGenVertexArrays(1)
        glBindVertexArray(self.vao)
        self.vbo = glGenBuffers(1)
        glBindBuffer(GL_ARRAY_BUFFER, self.vbo)
        glBufferData(GL_ARRAY_BUFFER, self.vertices.nbytes, self.vertices, GL_STATIC_DRAW)
        glEnableVertexAttribArray(0)
        glVertexAttribPointer(0, 3, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(0))
        glEnableVertexAttribArray(1)
        glVertexAttribPointer(1, 2, GL_FLOAT, GL_FALSE, 32, ctypes.c_void_p(12))
        
        self.RefinedVertCoords = []
        self.RefinedStCoords = []
        for i in range(self.vertex_count):
            offset = i * 8
            self.RefinedVertCoords.append(self.vertices[offset:(offset+3)])
            self.RefinedStCoords.append(self.vertices[(offset+3):((offset+3)+2)])
        for i in range(len(self.RefinedStCoords)):
            self.RefinedStCoords[i][0] = int(self.RefinedStCoords[i][0]*xSize)
            self.RefinedStCoords[i][1] = int(self.RefinedStCoords[i][1]*ySize)
        global xyz
        global st
        xyz = self.RefinedVertCoords
        st = self.RefinedStCoords
    
    def loadMesh(self, filepath):
        vertices = []
        v = []
        vt = []
        vn = []
        with open(filepath, 'r') as f:
            line = f.readline()
            while line:
                firstSpace = line.find(" ")
                flag = line[0:firstSpace]
                if flag == 'v':
                    line = line.replace('v ', '')
                    line = line.split(' ')
                    l = [float(i) for i in line]
                    v.append(l)
                elif flag == 'vt':
                    line = line.replace('vt ', '')
                    line = line.split(' ')
                    l = [float(i) for i in line]
                    vt.append(l)
                elif flag == 'vn':
                    line = line.replace('vn ', '')
                    line = line.split(' ')
                    l = [float(i) for i in line]
                    vn.append(l)
                elif flag == 'f':
                    line = line.replace('f ', '')
                    line = line.replace('\n', '')
                    line = line.split(' ')
                    faceVerts = []
                    faceTextures = []
                    faceNormals = []
                    for vertex in line:
                        l = vertex.split('/')
                        position = int(l[0]) - 1
                        faceVerts.append(v[position])
                        texture = int(l[1]) - 1
                        faceTextures.append(vt[texture])
                        normal = int(l[2]) - 1
                        faceNormals.append(vn[normal])
                    tris_amount = len(line) - 2
                    vertex_order = []
                    for i in range(tris_amount):
                        vertex_order.append(0)
                        vertex_order.append(i + 1)
                        vertex_order.append(i + 2)
                    for i in vertex_order:
                        for o in faceVerts[i]:
                            vertices.append(o)
                        for o in faceTextures[i]:
                            vertices.append(o)
                        for o in faceNormals[i]:
                            vertices.append(o)
                line = f.readline()
            return(vertices)
    
    def destroy(self):
        glDeleteVertexArrays(1, (self.vao,))
        glDeleteBuffers(1, (self.vbo,))

class Material:
    def __init__(self, filepath):
        self.texture = glGenTextures(1)
        glBindTexture(GL_TEXTURE_2D, self.texture)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_S, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_WRAP_T, GL_REPEAT)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MIN_FILTER, GL_NEAREST)
        glTexParameteri(GL_TEXTURE_2D, GL_TEXTURE_MAG_FILTER, GL_LINEAR)
        image = pg.image.load(filepath).convert()
        img_width, img_height = image.get_rect().size
        img_data = pg.image.tostring(image, "RGBA")
        glTexImage2D(GL_TEXTURE_2D, 0, GL_RGBA, img_width, img_height, 0, GL_RGBA, GL_UNSIGNED_BYTE, img_data)
        glGenerateMipmap(GL_TEXTURE_2D)
    
    def use(self):
        glActiveTexture(GL_TEXTURE0)
        glBindTexture(GL_TEXTURE_2D, self.texture)
    
    def destroy(self):
        glDeleteTextures(1, (self.texture,))

if __name__ == "__main__":
    myApp = App()
