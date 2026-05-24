"""nova bringup launcher with profiles.

Usage:
    ros2 launch nova_ops bringup.launch.py profile:=walk
    ros2 launch nova_ops bringup.launch.py profile:=sensors dry_run:=true
    ros2 launch nova_ops bringup.launch.py profile:=walk no_preflight:=true

Profile catalog: see nova_ops/bringup/__init__.py PROFILES dict.
"""
import sys

from launch import LaunchDescription
from launch.actions import (
    DeclareLaunchArgument, IncludeLaunchDescription, LogInfo, OpaqueFunction)
from launch.launch_description_sources import PythonLaunchDescriptionSource
from launch.substitutions import LaunchConfiguration
from launch_ros.actions import Node
from ament_index_python.packages import (
    get_package_share_directory, PackageNotFoundError)

from nova_ops.bringup import PROFILES, resolve_actions


def _compose(context, *args, **kwargs):
    profile_name = LaunchConfiguration('profile').perform(context)
    dry_run = LaunchConfiguration('dry_run').perform(context).lower() == 'true'
    no_preflight = (
        LaunchConfiguration('no_preflight').perform(context).lower() == 'true')

    if profile_name not in PROFILES:
        print(f'\n[bringup] unknown profile {profile_name!r}', file=sys.stderr)
        print('  available: ' + ', '.join(sorted(PROFILES.keys())),
              file=sys.stderr)
        return [LogInfo(msg=f'bringup ABORTED: unknown profile {profile_name!r}')]

    profile = PROFILES[profile_name]
    actions = resolve_actions(profile_name)

    out = [
        LogInfo(msg=f'=== nova bringup: profile={profile_name!r} ==='),
        LogInfo(msg=f'    {profile["description"]}'),
        LogInfo(msg=f'    {len(actions)} action(s) to launch'),
    ]
    if dry_run:
        out.append(LogInfo(msg='    DRY RUN — listing actions, NOT launching'))

    for action in actions:
        kind = action[0]
        if kind == 'launch':
            _, pkg, lf, lf_args = action
            label = f'launch {pkg}/{lf} {lf_args}'
            out.append(LogInfo(msg=f'  [{kind}] {label}'))
            if dry_run:
                continue
            try:
                share = get_package_share_directory(pkg)
            except PackageNotFoundError:
                out.append(LogInfo(
                    msg=f'    SKIP: package {pkg!r} not installed; '
                        f'see notes-qol-features.md / sensor SDK setup'))
                continue
            out.append(IncludeLaunchDescription(
                PythonLaunchDescriptionSource(f'{share}/launch/{lf}'),
                launch_arguments=list(lf_args.items()),
            ))
        elif kind == 'node':
            _, pkg, exe, params = action
            label = f'node {pkg}/{exe} params={params}'
            out.append(LogInfo(msg=f'  [{kind}] {label}'))
            if dry_run:
                continue
            try:
                get_package_share_directory(pkg)
            except PackageNotFoundError:
                out.append(LogInfo(
                    msg=f'    SKIP: package {pkg!r} not installed'))
                continue
            out.append(Node(
                package=pkg, executable=exe, output='screen',
                parameters=[params] if params else None,
            ))
        else:
            out.append(LogInfo(msg=f'  [unknown] {action}'))

    # Preflight gate — but we don't BLOCK launch, just log a reminder.
    # Real gating happens at the gait-controller level via the CLI exit
    # code (the gait controller's startup script should run
    # `ros2 run nova_ops preflight` and refuse to spawn the gait loop on
    # non-zero exit). Mention this loudly.
    if profile.get('preflight') and not no_preflight and not dry_run:
        out.append(LogInfo(
            msg='[bringup] gate: gait controller MUST run '
                '`ros2 run nova_ops preflight` and check exit code before '
                'enabling motion. Bringup does not enforce this.'))

    return out


def generate_launch_description():
    return LaunchDescription([
        DeclareLaunchArgument(
            'profile', default_value='bench',
            description=f'bringup profile name '
                        f'(one of: {", ".join(sorted(PROFILES.keys()))})'),
        DeclareLaunchArgument(
            'dry_run', default_value='false',
            description='if true, list actions without launching'),
        DeclareLaunchArgument(
            'no_preflight', default_value='false',
            description='skip the preflight reminder (intentional degraded test)'),
        DeclareLaunchArgument(
            'record', default_value='false',
            description='extend dashcam to record cameras + lidar for this run '
                        '(NOT yet wired — reserved; see notes-qol-features.md §4)'),
        OpaqueFunction(function=_compose),
    ])
