from glfw import KEY_ESCAPE, PRESS, MOUSE_BUTTON_LEFT, RELEASE,\
                 MOUSE_BUTTON_LEFT, init, create_window,\
                 make_context_current, set_key_callback,\
                 set_cursor_pos_callback,\
                 set_mouse_button_callback,\
                 set_window_size_callback, set_char_callback,\
                 set_scroll_callback, terminate, get_time,\
                 window_should_close, poll_events, swap_buffers,\
                 terminate, set_window_should_close,\
                 get_cursor_pos, get_window_size
from numpy import ones, array, eye, tan, radians, clip, pi, sum, square
from imgui import begin_main_menu_bar, begin_menu, end_menu,\
                  end_main_menu_bar, begin, slider_float, end,\
                  menu_item, new_frame, render, get_draw_data,\
                  get_io
from moderngl import DEPTH_TEST, CULL_FACE, TRIANGLES
from moderngl import create_context as mgl_C_C
from imgui import    create_context as imgui_C_C
from imgui.integrations.glfw import GlfwRenderer
from pywavefront import Wavefront
from scipy.spatial.transform import Rotation

class Mesh:
    """Simply contains an array of triangles and an array of normals.
    Could be enhanced, for instance with an element buffer"""
    def __init__(self, *args): 
        self.P, self.N = args 

class ObjMesh(Mesh):
    """An example of mesh loader, using the pywavefront module.
    Only load the first mesh of the file if there are more than one."""
    def __init__(self, filepath):
        for material in Wavefront(filepath).materials.values(): #una vez: material = scene.materials.values()
            data = array(material.vertices).reshape(-1, 6)
            self.P, self.N = data[:, 3:], data[:, :3]

        print(f"Loading mesh from {filepath}...\n\
              (Object has {len(self.P)//3} points)")

class RenderedMesh:
    """The equivalent of a Mesh, but stored in OpenGL buffers (on the GPU)
    ready to be rendered."""
    def __init__(self, ctx, mesh, program):
        self.mesh, (self.vboP, self.vboN) = mesh,\
                   (*(ctx.buffer(a.astype('f4').tobytes()) for\
                                          a in (mesh.P, mesh.N)),)
        self.vao =\
        ctx.vertex_array(program, ((a[0], '3f', a[1]) for a in\
              ((self.vboP, "in_vert"), (self.vboN, "in_normal"))))
        
    '''def release(self): #?
        (*(a.release() for a in\
                               (self.vboP, self.vboN, self.vao)),)'''

    def get_Vao(self):
        return self.vao

class App:
    def __init__(self, width = 640, height = 480,\
                 title = "Hello world"):    
        imgui_C_C()

        if init():
            self.window = create_window(width, height, title,\
                                                    None, None)

            if self.window:
                make_context_current(self.window)
                
                self.ctx, self.impl = mgl_C_C(require = 460),\
                    GlfwRenderer(self.window, attach_callbacks =\
                                                          False)
                set_key_callback(self.window, self._on_key)
                set_cursor_pos_callback(self.window,\
                                            self._on_mouse_move)
                set_mouse_button_callback(self.window,\
                                          self._on_mouse_button)
                set_window_size_callback(self.window,\
                                                 self._on_resize)
                set_char_callback(self.window, self._on_char)
                set_scroll_callback(self.window, self._on_scroll)

                self.init()
            
            else:   
                terminate()
                
    def main_loop(self):
        previous_time = get_time()

        # Loop until the user closes the window
        while not window_should_close(self.window):
            poll_events()
            self.impl.process_inputs()

            current_time = get_time()
            delta_time, previous_time =\
                        current_time - previous_time, current_time


            if self.camera.angular_velocity and not self.camera.previous_mouse_pos: #!!!!!!'''
                if sum(square(self.camera.angular_velocity)) < 1e-6:
                    self.angular_velocity = None

                else:
                    self.camera._rotate(*self.camera.momentum *\
                                        array(self.camera.angular_velocity))
            
            rot, rot1 =\
                 (*(Rotation.from_rotvec(eje * vec) for eje, vec in\
                  ((self.camera.rot_around_horizontal, array((1, 0, 0))),\
                   (self.camera.rot_around_vertical, array((0, 1, 0))))),)

            self.rot = Rotation.identity() * rot * rot1    
            viewMatrix = eye(4)
            viewMatrix[:3, :3] = self.rot.as_matrix()
            viewMatrix[:3, 3] = 0, 0, -self.camera._zoom
            self.camera.viewMatrix = viewMatrix

            ctx = self.ctx

            if "uPerspectiveMatrix" in self.program:
                self.program["uPerspectiveMatrix"].write(self.camera.perspectiveMatrix.T.astype('f4').tobytes())

            if "uViewMatrix" in self.program:
                self.program["uViewMatrix"].write(self.camera.viewMatrix.T.astype('f4').tobytes())

            ctx.screen.clear(*ones(3), -1) 
            ctx.enable_only(DEPTH_TEST | CULL_FACE)
            self.rendered_mesh.get_Vao().render(TRIANGLES)
           
            new_frame()

            """Use the imgui module here to draw the UI"""
            if begin_main_menu_bar():
                if begin_menu("File", True):
                    clicked_quit, selected_quit =\
                        menu_item("Quit", 'Esc', False, True)

                    if clicked_quit:
                        self.should_close()

                    end_menu()

                end_main_menu_bar()

            begin("Hello, world!", True)
            self.shape_need_update, (changed, self.some_slider) = False,\
                       slider_float("Some Slider", self.some_slider,
                       min_value = 0, max_value = 1, format = "%.02f")

            end()
            
            render()
            self.impl.render(get_draw_data())    
            swap_buffers(self.window)

        self.impl.shutdown()
        terminate()

    def should_close(self):
        set_window_should_close(self.window, True)

    def _on_key(self, window, key, *args): 
        self.impl.keyboard_callback(window, key, *args) 

        if key == KEY_ESCAPE:
            self.should_close()

    def _on_char(self, *args): 
        self.impl.char_callback(args) 

    def _on_mouse_move(self, window, *args): 
        self.impl.mouse_callback(window, *args)

        if self.camera.previous_mouse_pos: 
            self.camera._rotate(*array(args) - self.camera.previous_mouse_pos)

            self.camera.previous_mouse_pos = args

    def _on_mouse_button(self, window, button, action, mods):
        if not get_io().want_capture_mouse:
            if button == MOUSE_BUTTON_LEFT:
                p_M_P = None #no mola
                
                if action:
                    p_M_P = get_cursor_pos(self.window)

                self.camera.previous_mouse_pos = p_M_P

    def _on_scroll(self, window, *args): 
        self.impl.scroll_callback(window, *args)
        self.camera.zoom(args[1])

    def _on_resize(self, window, *args): 
        self.impl.resize_callback(window, *args)
        self.camera.resize(*args) 

        self.ctx.viewport = (0, 0, *args) 

def perspective(fovy, aspect, near, far):
    top = near * tan(fovy / 2)
    right = top * aspect
    n, f, t, b, l, r = near, far, top, -top, -right, right
    
    return array(((2 / (r - l) * n, 0, (r + l) / (r - l), 0),
                  (0, 2 / (t - b) * n, (t + b) / (t - b), 0),
                  (0, 0, -(f + n) / (f - n),\
                   -2 * n * f / (f - n)), (0, 0, -1, 0)))

class Camera:
    def __init__(self, *args): 
        self.sensitivity, self.zoom_sensitivity, self.momentum,\
                          self._zoom, self.rot,\
                          self.previous_mouse_pos,\
                          self.angular_velocity,\
                          self.rot_around_vertical,\
                          self.rot_around_horizontal =\
                          1/100, 1/10, 0.93, 2,\
                          Rotation.identity(), None, None, 0, 0

        self.resize(*args)

    def resize(self, width, height):
        self.perspectiveMatrix = perspective(radians(80),\
                                             width / height,\
                                             1/100, 100)

    def zoom(self, steps):
        self._zoom *= (1 - self.zoom_sensitivity) ** steps

    def _rotate(self, *args):
        self.rot_around_vertical, self.rot_around_horizontal =\
                                                self.sensitivity * array(args) +\
                            (self.rot_around_vertical, self.rot_around_horizontal)
        pi_Medios = pi / 2
        self.rot_around_horizontal =\
                                clip(self.rot_around_horizontal,\
                                     -pi_Medios, pi_Medios)
        self.angular_velocity = args

class MyApp(App):
    def init(self):
        ctx = self.ctx
        ''' Load a mesh
         Load the glsl program'''
        self.mesh, self.program =\
                   ObjMesh("dragon.obj"),\
                   ctx.program(vertex_shader =\
        '''#version 460
        in vec3 in_vert, in_normal;

        out vec3 v_normal, v_position;

        uniform mat4 uPerspectiveMatrix = mat4(0),\
                     uViewMatrix = mat4(0);

        void main() {
            v_normal = in_normal;
            v_position = in_vert;
            gl_Position = uPerspectiveMatrix * uViewMatrix *\
                          vec4(v_position, 1);
        }''', fragment_shader=\
        '''#version 460
        in vec3 v_normal, v_position;

        out vec4 f_color;

        uniform vec4 uColor = vec4(1, 0.5, 0.1, 1);
        uniform mat4 uViewMatrix = mat4(0);
        uniform float uHardness = 16;

        const vec3 lightpos0 = vec3(22, 16, 50),\
                   lightcolor0 = vec3(1, 0.95, 0.9),\
                   lightpos1 = vec3(-22, -8, -50),\
                   lightcolor1 = vec3(0.9, 0.95, 1),\
                   ambient = vec3(1);

        float get_Max_Dot(vec3 v, vec3 v1) {
            return max(0, dot(v, v1));
        }

        vec3 get_C(vec3 lightpos, vec3 v_position, vec3 n, vec3 c,\
                  vec4 uColor, vec3 lightcolor, vec3 r, vec3 v,\
                  float uHardness, float spec) {
            vec3 l = normalize(lightpos - v_position);
            float s = get_Max_Dot(n, l);
            c += uColor.rgb * s * lightcolor;

            if (s > 0) {
                r = reflect(-l, n);
                spec = pow(get_Max_Dot(v, r), uHardness);
                c += spec * lightcolor;
            }

            return c;
        }
            
        void main() {
            // This is a very basic lighting, for visualization only //
            vec3 viewpos = inverse(uViewMatrix)[3].xyz,\
            n = normalize(v_normal), c = uColor.rgb * ambient,\
                     v = normalize(viewpos - v_position), r;
            float spec = 0;
 
            c = get_C(lightpos1, v_position, n, get_C(lightpos0, v_position, n, c, uColor,\
                 lightcolor0, r, v, uHardness, spec), uColor,\
                 lightcolor1, r, v, uHardness, spec); //lado, lado1, recursiva -> iterativa

            f_color = vec4(c / 2, uColor.a);
        }''')
        ''' Create the rendered mesh from the mesh and the program
         Setup camera
         Initialize some value used in the UI'''
        self.rendered_mesh, self.camera, self.some_slider =\
                            RenderedMesh(ctx, self.mesh, self.program),\
                            Camera(*get_window_size(self.window)), 0.42

MyApp(1280, 720, "Python 3d Viewer").main_loop()


