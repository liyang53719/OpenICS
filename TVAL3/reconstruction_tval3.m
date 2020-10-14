% reconstruction_tval3.m
% 
% Uses TVAL3 reconstruction method.
% 
% Usage: x_hat = reconstruction_tval3(x,y,input_channel,input_width,input_height,A,At,specifics)
%
% x - nx1 vector, original signal
%
% y - mx1 vector, observations
%
% input_channel - Channels in the original image
%
% input_width - Width of the original image
%
% input_height - Height of the original image
%
% A - Function handle to sensing method
%
% At - Function handle to transposed sensing method
%
% specifics - Map that must contain at least the following arguments:
%
%   TVL2 - Whether to use the TVL2 algorithm.
%       Default: false
%
%   TVnorm - The L-norm to use. Either 1 (anisotropic) or 2 (isotropic).
%       Default: 2
%
%   nonneg - Whether to use nonnegative models.
%       Default: false
%
%   mu - The primary penalty parameter.
%       Default: 2^8
%
%   beta - The secondary penalty parameter.
%       Default: 2^5
%
%   tol - The outer stopping tolerance.
%       Default: 1e-6
%
%   tol_inn - The inner stopping tolerance.
%       Default: 1e-3
%
%   maxit - The maximum total iterations.
%       Default: 1025
%
%   maxcnt - The maximum outer iterations.
%       Default: 10
%
%   isreal - If the signal is real.
%       Default: false
%
%   disp - Whether info should be printed each iteration.
%       Default: false
%
%   init - The initial guess of the algorithm.
%       Default: none
%
%   scale_A - Whether A should be scaled.
%       Default: true
%
%   scale_b - Whether b should be scaled.
%       Default: true
%
%   consist_mu - Whether mu should be scaled along with A and b.
%       Default: false
%
%   mu0 - The initial value of mu.
%       Default: specifics.mu
%
%   beta0 - The initial value of beta.
%       Default: specifics.beta
%
%   rate_ctn - The continuation rate of the penalty parameters.
%       Default: 2
%
%   c - The nonmonotone line search tolerance modifier.
%       Default: 1e-5
%
%   gamma - Nonmonotone line search alpha continuation parameter.
%       Default: 0.6
%
%   gam - Controls the degree of nonmonotonicity. 0 = monotone line search.
%       Default: 0.9995
%
%   rate_gam - Shrinkage rate of gam.
%       Default: 0.9
%
%   normalization - Whether the image should be normalized. May help make
%                   the image sparser and improve reconstruction accuracy.
%       Default: false
%

function x_hat = reconstruction_tval3(x, y, input_channel, input_width, input_height, A, At, specifics)

    % set default values
    if ~isfield(specifics, 'normalization')
        specifics.normalization = false;
    end
    
    % apply normalization to image
    if specifics.normalization
        x_norm = norm(x(:));
        x = x / x_norm;
        x_mean = mean(x(:));
        x = x - x_mean;
        y = A(x(:));
    end
    
    % TVAL3 implementation structures function differently
    function out = A_handles(z, mode)
        switch mode
            case 1
                out = A(z(:));
            case 2
                out = At(z(:));
            otherwise
                error('Unknown mode passed into A_handles!');
        end
    end

    time0 = clock;
    [x_hat, hist] = TVAL3(@A_handles, y, input_height, input_width, specifics);
    fprintf('Total elapsed time = %f secs\n\n', etime(clock,time0));
    
    % invert normalization
    if specifics.normalization
        x_hat = x_hat + x_mean;
        x_hat = x_hat * x_norm;
    end
end