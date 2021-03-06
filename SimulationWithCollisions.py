from os.path import join
from numpy import random, ones, concatenate
from pandas import read_excel
from scipy.constants import pi, N_A, e
import matplotlib.pyplot as plt
from scipy.interpolate import interp1d

from Collisions.CoulombCollision import coulomb_collision
from Collisions.ElasticCollision import elastic_collision
from Collisions.NeutralGas import NeutralGas
from Field.FieldInterpolation.FieldInterpolation3D import FieldInterpolation3D
from Field.FieldInterpolation.FieldInterpolationRadial import FieldInterpolationRadial
from Particle.Particle import Particle
from InitBeamConditions.GeneratePositionDistribution import gen_positions
from InitBeamConditions.GenerateVelocityDistribution import gen_velocities
from Field.FieldLoad.ElectricFieldLoad import load_radial_electric_field
from Field.FieldLoad.MagneticFieldLoad import load_magnetic_field_3d
from TrackParticles.TrackTrajectory import TrackTraj
from Visualization.PlotBeamTrajectory import plot_traj_multy_ptcls_type


def simulation(n_total, init_pos, energy_range, vel_theta, dt, it_num, gas, seed=None):
    assert n_total % 12 == 0
    random.seed(seed)
    quantity = n_total / 3
    m_235 = ones(quantity / 4) * 0.235 / N_A # U
    m_238 = ones(quantity / 4) * 0.238 / N_A # U
    m_239 = ones(quantity / 4) * 0.239 / N_A # Pt
    m_240 = ones(quantity / 4) * 0.240 / N_A # Pt
    m_137 = ones(quantity) * 0.137 / N_A # Cs
    m_90 = ones(quantity) * 0.09 / N_A # Sr
    mass = concatenate((m_235, m_238, m_239, m_240, m_137, m_90))
    charge = ones(n_total) * e

    r, efr = load_radial_electric_field(join('FieldData', 'PenningPotentialApproximated.xlsx'))
    efr_interp = FieldInterpolationRadial(radial_grid=r, radial_field=efr)
    grid, mf = load_magnetic_field_3d(dirpath=join('FieldData', 'MagneticField_2_coils'))
    for i in range(mf.shape[0]):
        mf[i] *= 1.5
    mf_interp = FieldInterpolation3D(grid=grid, field=mf)

    beam = Particle(mass=mass,
                    charge=charge,
                    pos=gen_positions(pos=init_pos, sub_width=0.01, n_total=n_total),
                    vel=gen_velocities(energy_range=energy_range, mass=mass, theta=vel_theta),
                    electric_field_interp_func=efr_interp.interp_func,
                    magnetic_field_interp_func=mf_interp.interp_func,
                    )

    collision_prob_data = None
    if gas.name == 'Ar':
        collision_prob_data = read_excel(join('CollisionData', 'ArG.xlsx'), header=None)
    if gas.name == 'He':
        collision_prob_data = read_excel(join('CollisionData', 'HeG.xlsx'), header=None)

    f1 = interp1d(collision_prob_data[0].values, collision_prob_data[1].values, fill_value='extrapolate')
    f2 = interp1d(collision_prob_data[0].values, collision_prob_data[2].values, fill_value='extrapolate')
    f3 = interp1d(collision_prob_data[0].values, collision_prob_data[3].values, fill_value='extrapolate')
    f4 = interp1d(collision_prob_data[0].values, collision_prob_data[4].values, fill_value='extrapolate')
    g_sigma = [(m_235[0], f1), (m_238[0], f1), (m_239[0], f2), (m_240[0], f2), (m_137[0], f3), (m_90[0], f4)]

    track_beam = TrackTraj(beam)

    from time import time
    t0 = time()
    beam.vel_push(dt=-0.5 * dt)
    for it in range(it_num):
        beam.push(dt=dt)
        beam.electric_field_interp()
        beam.magnetic_field_interp()
        elastic_collision(ptcl_beam=beam, n_total=n_total, dt=dt, gas=gas, g_sigma=g_sigma)
        #coulomb_collision(beam, n_total, dt, gas, it)
        if it % 100 == 0:
            track_beam.track_traj()
    print 'simulation time:', time() - t0

    x, y, z = track_beam.get_traj()
    plt.figure(figsize=(5, 5))
    plt.xlim((-0.3, 0.3))
    plt.ylim((-0.3, 0.3))
    #fig, axs = plt.subplots(3, 3)
    plot_traj_multy_ptcls_type(x, y, ptcl_type_num=3, colors=('blue', 'green', 'red'),
                               labels=('m = 235', '120 < m < 160', '70 < m < 120'),
                               alpha=0.3, xlabel='x, meter', ylabel='y, meter', fig=plt)
    plt.show()
    return track_beam


if __name__ == '__main__':
    Ar = NeutralGas(T=300, n=1e20, mass=6.6335209E-26, name='Ar')
    He = NeutralGas(T=300, n=6e20, mass=6.6464764E-27, name='He')
    simulation(n_total=120,
               init_pos=(0.25, 0, 0),
               energy_range=(1 * e, 20 * e),
               vel_theta=(0, pi / 6),
               it_num=10000,
               dt=1e-8,
               seed=1,
               gas=Ar,
               )
    fig = plt.gcf()
    fig.set_size_inches(6, 6, forward=True)
