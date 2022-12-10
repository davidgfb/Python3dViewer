from moderngl import DEPTH_TEST, CULL_FACE
from glfw import KEY_ESCAPE, PRESS, MOUSE_BUTTON_LEFT, RELEASE,\
                 MOUSE_BUTTON_LEFT
from numpy import ones
from imgui import begin_main_menu_bar, begin_menu, end_menu,\
                  end_main_menu_bar, begin, slider_float, end,\
                  menu_item
from augen import App, Camera
from augen.mesh import ObjMesh, RenderedMesh

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


