from launch import LaunchDescription
from launch.actions import DeclareLaunchArgument, IncludeLaunchDescription
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import Command, FindExecutable, LaunchConfiguration, PathJoinSubstitution
from launch_ros.actions import Node
from launch_ros.parameter_descriptions import ParameterValue
from launch_ros.substitutions import FindPackageShare

def generate_launch_description():
    pkg = FindPackageShare("ur3_natural_motion_preview")
    ur_desc = FindPackageShare("ur_description")

    calibration = LaunchConfiguration("kinematics_params")
    workpoint_file = LaunchConfiguration("workpoint_file")
    step_mode = LaunchConfiguration("step_mode")
    loop = LaunchConfiguration("loop")

    robot_description = ParameterValue(
        Command([
            FindExecutable(name="xacro"), " ",
            PathJoinSubstitution([ur_desc, "urdf", "ur.urdf.xacro"]), " ",
            "ur_type:=ur3 ",
            "name:=ur ",
            "kinematics_params:=", calibration, " ",
            "safety_limits:=true ",
        ]),
        value_type=str,
    )

    moveit_launch = IncludeLaunchDescription(
        PythonLaunchDescriptionSource(
            PathJoinSubstitution([
                FindPackageShare("ur_moveit_config"),
                "launch",
                "ur_moveit.launch.py",
            ])
        ),
        launch_arguments={
            "ur_type": "ur3",
            "launch_rviz": "false",
            "launch_servo": "false",
            "publish_robot_description_semantic": "true",
        }.items(),
    )

    return LaunchDescription([
        DeclareLaunchArgument(
            "kinematics_params",
            default_value="/home/rosystem/ur3_factory_calibration.yaml",
        ),
        DeclareLaunchArgument(
            "workpoint_file",
            default_value=PathJoinSubstitution([
                pkg, "config", "packing_workpoints.yaml"
            ]),
        ),
        DeclareLaunchArgument("step_mode", default_value="false"),
        DeclareLaunchArgument("loop", default_value="true"),

        # Description only. No ros2_control node and no physical UR driver.
        Node(
            package="robot_state_publisher",
            executable="robot_state_publisher",
            output="screen",
            parameters=[{"robot_description": robot_description}],
        ),

        moveit_launch,

        Node(
            package="ur3_natural_motion_preview",
            executable="preview_node",
            output="screen",
            parameters=[{
                "workpoint_file": workpoint_file,
                "step_mode": ParameterValue(step_mode, value_type=bool),
                "loop": ParameterValue(loop, value_type=bool),
            }],
        ),

        Node(
            package="rviz2",
            executable="rviz2",
            output="screen",
            arguments=["-d", PathJoinSubstitution([
                pkg, "rviz", "preview.rviz"
            ])],
            parameters=[{"robot_description": robot_description}],
        ),
    ])
