from moderngl import DEPTH_TEST, CULL_FACE
from glfw import KEY_ESCAPE, PRESS, MOUSE_BUTTON_LEFT, RELEASE,\
                 MOUSE_BUTTON_LEFT
from numpy import ones
from imgui import begin_main_menu_bar, begin_menu, end_menu,\
                  end_main_menu_bar, begin, slider_float, end,\
                  menu_item

from augen.mesh import ObjMesh, RenderedMesh

import glfw
import moderngl
import imgui
from imgui.integrations.glfw import GlfwRenderer as ImguiRenderer

class App:
    def __init__(self, width = 640, height = 480, title = "Hello world"):
        imgui.create_context()

        if not glfw.init():
            return
        
        self.window = glfw.create_window(width, height, title, None, None)
        if not self.window:
            glfw.terminate()
            return

        glfw.make_context_current(self.window)
        self.ctx = moderngl.create_context(require=460)

        self.impl = ImguiRenderer(self.window, attach_callbacks=False)
        
        glfw.set_key_callback(self.window, self._on_key)
        glfw.set_cursor_pos_callback(self.window, self._on_mouse_move)
        glfw.set_mouse_button_callback(self.window, self._on_mouse_button)
        glfw.set_window_size_callback(self.window, self._on_resize)
        glfw.set_char_callback(self.window, self._on_char)
        glfw.set_scroll_callback(self.window, self._on_scroll)

        self.init()

    def main_loop(self):
        previous_time = glfw.get_time()

        # Loop until the user closes the window
        while not glfw.window_should_close(self.window):
            glfw.poll_events()
            self.impl.process_inputs()

            current_time = glfw.get_time()
            delta_time = current_time - previous_time
            previous_time = current_time
            self.update(current_time, delta_time)
            self.render()

            imgui.new_frame()
            self.ui()
            imgui.render()
            self.impl.render(imgui.get_draw_data())

            glfw.swap_buffers(self.window)

        self.impl.shutdown()
        glfw.terminate()

    def should_close(self):
        glfw.set_window_should_close(self.window, True)

    def mouse_pos(self):
        return glfw.get_cursor_pos(self.window)

    def size(self):
        return glfw.get_window_size(self.window)

    def init(self):
        pass

    def update(self, time):
        pass

    def render(self):
        pass

    def ui(self):
        pass

    def _on_key(self, window, key, scancode, action, mods):
        self.impl.keyboard_callback(window, key, scancode, action, mods)
        self.on_key(key, scancode, action, mods)

    def on_key(self, key, scancode, action, mods):
        pass

    def _on_char(self, window, codepoint):
        self.impl.char_callback(window, codepoint)
        self.on_char(codepoint)

    def on_char(self, codepoint):
        pass

    def _on_mouse_move(self, window, x, y):
        self.impl.mouse_callback(window, x, y)
        self.on_mouse_move(x, y)

    def on_mouse_move(self, x, y):
        pass

    def _on_mouse_button(self, window, button, action, mods):
        if not imgui.get_io().want_capture_mouse:
            self.on_mouse_button(button, action, mods)

    def on_mouse_button(self, button, action, mods):
        pass

    def _on_scroll(self, window, xoffset, yoffset):
        self.impl.scroll_callback(window, xoffset, yoffset)
        self.on_scroll(xoffset, yoffset)

    def on_scroll(self, xoffset, yoffset):
        pass

    def _on_resize(self, window, width, height):
        self.impl.resize_callback(window, width, height)
        self.on_resize(width, height)

    def on_resize(self, width, height):
        pass

import numpy as np
from scipy.spatial.transform import Rotation


import numpy as np

def _perspective(n, f, t, b, l, r):
    return np.array([
        [ 2*n/(r-l),     0    ,   (r+l)/(r-l) ,       0        ],
        [     0    , 2*n/(t-b),   (t+b)/(t-b) ,       0        ],
        [     0    ,     0    , -((f+n)/(f-n)), -(2*n*f/(f-n)) ],
        [     0    ,     0    ,       -1      ,       0        ],
    ])

def perspective(fovy, aspect, near, far):
    top = near * np.tan(fovy / 2)
    right = top * aspect
    return _perspective(near, far, top, -top, -right, right)



class Camera:
    def __init__(self, width, height):
        self.sensitivity = 0.01
        self.zoom_sensitivity = 0.1
        self.momentum = 0.93

        self._zoom = 2
        self.rot = Rotation.identity()
        self.previous_mouse_pos = None
        self.angular_velocity = None
        self.rot_around_vertical = 0
        self.rot_around_horizontal = 0
        self.resize(width, height)

    def resize(self, width, height):
        self.perspectiveMatrix = perspective(np.radians(80), width/height, 0.01, 100.0)

    def zoom(self, steps):
        self._zoom *= pow(1 - self.zoom_sensitivity, steps)

    def update(self, time, delta_time):
        if self.previous_mouse_pos is None and self.angular_velocity is not None:
            self._damping()

        self.rot = Rotation.identity()
        self.rot *= Rotation.from_rotvec(self.rot_around_horizontal * np.array([1,0,0]))
        self.rot *= Rotation.from_rotvec(self.rot_around_vertical * np.array([0,1,0]))

        viewMatrix = np.eye(4)
        viewMatrix[:3,:3] = self.rot.as_matrix()
        viewMatrix[0:3,3] = 0, 0, -self._zoom
        self.viewMatrix = viewMatrix

    def set_uniforms(self, program):
        if "uPerspectiveMatrix" in program:
            program["uPerspectiveMatrix"].write(self.perspectiveMatrix.T.astype('f4').tobytes())
        if "uViewMatrix" in program:
            program["uViewMatrix"].write(self.viewMatrix.T.astype('f4').tobytes())

    def start_rotation(self, x, y):
        self.previous_mouse_pos = x, y

    def update_rotation(self, x, y):
        if self.previous_mouse_pos is None:
            return
        sx, sy = self.previous_mouse_pos
        dx = x - sx
        dy = y - sy
        self._rotate(dx, dy)
        self.previous_mouse_pos = x, y

    def stop_rotation(self):
        self.previous_mouse_pos = None

    def _rotate(self, dx, dy):
        self.rot_around_vertical += dx * self.sensitivity
        self.rot_around_horizontal += dy * self.sensitivity
        self.rot_around_horizontal = np.clip(self.rot_around_horizontal, -np.pi / 2, np.pi / 2)
        self.angular_velocity = dx, dy

    def _damping(self):
        dx, dy = self.angular_velocity
        if dx * dx + dy * dy < 1e-6:
            self.angular_velocity = None
        else:
            self._rotate(dx * self.momentum, dy * self.momentum)



class MyApp(App):
    def init(self):
        ctx = self.ctx
        # Load a mesh
        # Load the glsl program
        self.mesh, self.program =\
                   ObjMesh("sample-data/dragon.obj"),\
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
        # Create the rendered mesh from the mesh and the program
        # Setup camera
        self.rendered_mesh, (w, h) = RenderedMesh(ctx, self.mesh,\
                                        self.program), self.size()
        # Initialize some value used in the UI
        self.camera, self.some_slider = Camera(w, h), 0.42
        
    def update(self, time, delta_time):
        # Update damping effect (and internal matrices)
        self.camera.update(time, delta_time)

    def render(self):
        ctx = self.ctx
        self.camera.set_uniforms(self.program)
        ctx.screen.clear(*ones(3), -1) 
        ctx.enable_only(DEPTH_TEST | CULL_FACE)
        self.rendered_mesh.render(ctx)

    def on_key(self, key, scancode, action, mods):
        if key == KEY_ESCAPE:
            self.should_close()

    def on_mouse_move(self, x, y):
        self.camera.update_rotation(x, y)

    def on_mouse_button(self, button, action, mods):
        if action == PRESS and button == MOUSE_BUTTON_LEFT:
            self.camera.start_rotation(*self.mouse_pos())

        if action == RELEASE and button == MOUSE_BUTTON_LEFT:
            self.camera.stop_rotation()

    def on_resize(self, width, height):
        self.camera.resize(width, height)
        self.ctx.viewport = (0, 0, width, height)

    def on_scroll(self, x, y):
        self.camera.zoom(y)

    def ui(self):
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
        self.shape_need_update = False
        changed, self.some_slider =\
                 slider_float("Some Slider", self.some_slider,
                   min_value = 0, max_value = 1, format = "%.02f")

        end()

MyApp(1280, 720, "Python 3d Viewer - Elie Michel").main_loop()


