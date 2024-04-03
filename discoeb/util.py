import jax
import jax.numpy as jnp

def lngamma_complex_e( z : complex ):
  """Log[Gamma(z)] for z complex, z not a negative integer Uses complex Lanczos method. Note that the phase part (arg)
    is not well-determined when |z| is very large, due to inevitable roundoff in restricting to (-Pi,Pi].
    -- adapted from GSL --
 
   Args:
      z (complex): input value

  Returns:
      complex: lnr + i arg, where lnr = log|Gamma(z)|, arg = arg(Gamma(z))  in (-Pi, Pi]
  """
  def lngamma_lanczos_complex( z : complex ):
    # Lanzcos approximation [J. SIAM Numer. Anal, Ser. B, 1 (1964) 86]
    lanczos_7_c = jnp.array([
      0.99999999999980993227684700473478,
      676.520368121885098567009190444019,
    -1259.13921672240287047156078755283,
      771.3234287776530788486528258894,
    -176.61502916214059906584551354,
      12.507343278686904814458936853,
    -0.13857109526572011689554707,
      9.984369578019570859563e-6,
      1.50563273514931155834e-7
    ])
    LogRootTwoPi_ = 0.9189385332046727418
    z  = z - 1.0
    Ag = lanczos_7_c[0] + jnp.sum( lanczos_7_c[1:] / jnp.abs(z+jnp.arange(1,9))**2 * jnp.conj(z+jnp.arange(1,9)))
    return (z+0.5)*jnp.log(z+7.5) - (z+7.5) + LogRootTwoPi_ + jnp.log(Ag)
  
  lnpi = 1.14472988584940017414342735135
  return jax.lax.cond( jnp.real(z) <= 0.5, 
                      lambda zz: lnpi - jnp.log( jnp.sin(jnp.pi*zz) ) - lngamma_lanczos_complex(1.0-zz), 
                      lambda zz: lngamma_lanczos_complex(zz), z )


def root_find_bisect( *, func, xleft, xright, numit, param ):
  """
  Simple bisection routine for root finding.
  
  Parameters
  ----------
  func : function
    Function to be evaluated.
  xleft : float
    Left boundary of the interval.
  xright : float
    Right boundary of the interval.
  numit : int
    Number of iterations.

  Returns
  -------
  x0 : float
    Approximation to the root, given by the midpoint of the final interval.

  """
  for i in range(numit):
        xmid = 0.5 * (xleft + xright)
        xleft, xright = jax.lax.cond(func(xmid, param) * func(xleft, param) > 0, lambda x : (xmid, xright), lambda x : (xleft, xmid), None )
  # def body(carry, i):
  #   xleft, xright, param = carry
  #   xmid = 0.5 * (xleft + xright)
  #   carry = jax.lax.cond(func(xmid, param) * func(xleft, param) > 0, lambda x : (xmid, xright, param), lambda x : (xleft, xmid, param), None )
  #   return carry, xmid

  # (xleft, xright, param), _ = jax.lax.scan(body, (xleft, xright, param), jnp.arange(numit))
  return 0.5 * (xleft + xright)


def softclip(x, a_min, a_max):
    """
    Softclip function that is strictly monotonous.
    """
    y = jnp.clip(x, a_min, a_max)
    return jnp.where(x < a_min, a_min + jnp.log(jnp.abs(x - a_min) + 1) * jnp.sign(x - a_min), jnp.where(x > a_max, a_max + jnp.log(jnp.abs(x - a_max) + 1) * jnp.sign(x - a_max), y))


def savgol_filter( *, y : jax.Array, window_length : int, polyorder : int ) -> jax.Array:
    """ Savitzky-Golay filter for 1D data.
    
    Args:
        y (array_like)          : the input array
        window_length (int)     : the length of the filter window
        polyorder (int)         : the order of the polynomial
        
    Returns:
        y_smoothed (array_like) : the smoothed array
    """
    if window_length % 2 == 0:
        raise ValueError('window_length must be odd')
    if window_length < polyorder + 2:
        raise ValueError('window_length is too small for the polynomials order')
    if window_length > y.shape[0]:
        raise ValueError('window_length is too large for input array')
    if polyorder > window_length:
        raise ValueError('polyorder is too large for the window length')
    if polyorder < 1:
        raise ValueError('polyorder must be non-negative')
    
    # Precompute the coefficients
    b = jnp.array([(-1)**i for i in range(polyorder+1)])
    A = jnp.vander(jnp.linspace(-1, 1, window_length), polyorder+1)
    AT = jnp.transpose(A)
    ATA = jnp.dot(AT, A)
    ATb = jnp.dot(AT, b)
    c = jnp.linalg.solve(ATA, ATb)
    
    # Apply the filter
    y_smoothed = jnp.zeros_like(y)
    for i in range(window_length//2, y.shape[0]-window_length//2):
        y_smoothed = jax.ops.index_update(y_smoothed, i, jnp.dot(c, y[i-window_length//2:i+window_length//2+1]))
    
    return y_smoothed