function [rec_im PSNR SSIM]   =  NLR_CS_Reconstruction( par, A, At  )
time0            =    clock;
y                =    par.y;
rec_im0          =    DCT_CIR( y, par, A, At );

rec_im           =    rec_im0;
AtY              =    At(y);
beta             =    0.01;
M                =    zeros( size(rec_im) );
M(par.picks)     =    1;
M(1,1)           =    1;
DtY              =    zeros( size(rec_im) );
DtY(1,1)         =    y(1);
K                =    length(y);

% modified to round indices to suppress warning
DtY(par.picks)   =    y(2:ceil((K+1)/2)) + i*y(floor((K+3)/2):K);

[h, w]           =    size( rec_im );
cnt              =    0;
iters            =    15;
for  k    =   1 : par.K
    
    blk_arr      =     Block_matching( rec_im, par);
    f            =     rec_im;
    U_arr        =     zeros(par.win^4, size(blk_arr,2), 'single');
    if (k<=par.K0)  flag=0;  else flag=1;  end        
    
    for it  =  1 : iters
    
        cnt      =   cnt  +  1;    
        if (mod(cnt, 20) == 0)
            if isfield(par,'ori_im')
                PSNR     =   csnr( f, par.ori_im, 0, 0 );
                fprintf( 'NLR CS Reconstruction, Iter %d : PSNR = %f \n', cnt, PSNR );
            end
        end
        
        [rim, wei, U_arr]      =   Low_rank_appro(f, par, blk_arr, U_arr, it, flag );   
        rim     =    (rim+beta*f)./(wei+beta);
        
        if par.s_model == 1
            b               =   AtY + beta * rim(:);
            [X flag0]       =   pcg( @(x) Afun(x, At, A, beta, wei(:)), b, 0.5E-6, 400, [], [], f(:));          
            f               =   reshape(X, h, w);  
        else                        
            f       =    ifft2( (DtY + beta * fft2(rim)) ./ (M + beta) );
        end
    end
    rec_im    =   f;
    % beta       =   beta * 1.05;
end

if isfield(par,'ori_im')
    PSNR     =   csnr( rec_im, par.ori_im, 0, 0 );
    SSIM      =  cal_ssim( rec_im, par.ori_im, 0, 0 );
end
disp(sprintf('Total elapsed time = %f min\n', (etime(clock,time0)/60) ));
return;


%======================================================
function  y  =  Afun(x, At, A, eta, Wei)
y      =   At( A(x) ) + eta*x;  % eta * (Wei.*x);
return;



function   [dim, wei, U_arr]  =  Low_rank_appro(nim, par, blk_arr, U_arr, it, flag)
b            =   par.win;
[h  w ch]    =   size(nim);
N            =   h-b+1;
M            =   w-b+1;
r            =   [1:N];
c            =   [1:M]; 

X            =   Im2Patch( nim, par );
Ys           =   zeros( size(X) );        
W            =   zeros( size(X) );
L            =   size(blk_arr,2);
T            =   4; 
for  i  =  1 : L
    B          =   X(:, blk_arr(:, i));
    mB         =   repmat(mean( B, 2 ), 1, size(B, 2));
    B          =   B-mB;
    if it==1 || mod(it, T)==0
        [tmp_y, tmp_w, U_arr(:,i)]   =   Weighted_SVT( double(B), par.c1, par.nSig^2, mB, flag, par.c0 );
    else
        [tmp_y, tmp_w]   =   Weighted_SVT_fast( double(B), par.c1, par.nSig^2, mB, U_arr(:,i), flag, par.c0 );
    end
    Ys(:, blk_arr(:,i))   =   Ys(:, blk_arr(:,i)) + tmp_y;
    W(:, blk_arr(:,i))    =   W(:, blk_arr(:,i)) + tmp_w;
end

dim     =  zeros(h,w);
wei     =  zeros(h,w);
k       =   0;
for i  = 1:b
    for j  = 1:b
        k    =  k+1;
        dim(r-1+i,c-1+j)  =  dim(r-1+i,c-1+j) + reshape( Ys(k,:)', [N M]);
        wei(r-1+i,c-1+j)  =  wei(r-1+i,c-1+j) + reshape( W(k,:)', [N M]);
    end
end
return;



function  [X W U]   =   Weighted_SVT( Y, c1, nsig2, m, flag, c0 )
c1                =   c1*sqrt(2);
[U0,Sigma0,V0]    =   svd(full(Y),'econ');
Sigma0            =   diag(Sigma0);
if flag==1
    S                 =   max( Sigma0.^2/size(Y, 2), 0 );
    thr               =   c1*nsig2./ ( sqrt(S) + eps );
    S                 =   soft(Sigma0, thr);
else
    S                 =   soft(Sigma0, c0*nsig2);
end
r                 =   sum( S>0 );
U                 =   U0(:,1:r);
V                 =   V0(:,1:r);
X                 =   U*diag(S(1:r))*V';
if r==size(Y,1)
    wei           =   1/size(Y,1);
else
    wei           =   (size(Y,1)-r)/size(Y,1);
end
W                 =   wei*ones( size(X) );
X                 =   (X + m)*wei;
U                 =   U0(:);
return;



function  [X W]   =   Weighted_SVT_fast( Y, c1, nsig2, m, U0, flag, c0 )
c1                =   c1*sqrt(2);
n                 =   sqrt(length(U0));
U0                =   reshape(U0, n, n);
A                 =   U0'*Y;
Sigma0            =   sqrt( sum(A.^2, 2) );
V0                =   (diag(1./Sigma0)*A)';

if flag==1
    S                 =   max( Sigma0.^2/size(Y, 2) - 0*nsig2, 0 );
    thr               =   c1*nsig2./ ( sqrt(S) + eps );
    S                 =   soft(Sigma0, thr);
else
    S                 =   soft(Sigma0, c0*nsig2);
end
r                 =     sum( S>0 );
P                 =     find(S);
X                 =     U0(:,P)*diag(S(P))*V0(:,P)';
if r==size(Y,1)
    wei           =     1/size(Y,1);
else
    wei           =     (size(Y,1)-r)/size(Y,1);
end
W                 =     wei*ones( size(X) );
X                 =     (X + m)*wei;
return;



%====================================================================
% Compressive Image Recovery Using DCT 
%--------------------------------------------------------------------
function  Rec_im0    =   DCT_CIR( y, par, A, At )
ori_im      =    par.ori_im;
[h w]       =    size(ori_im);
im          =    At( y );
im          =    reshape(im,[h w]);

lamada      =    1.5;  % 1.8, 1.2-1.7
b           =    par.win*par.win;
D           =    dctmtx(b);

for k   =  1:1
    f      =   im;
    for  iter = 1 : 300   
        
        if (mod(iter, 50) == 0)
            if isfield(par,'ori_im')
                PSNR     =   csnr( f, par.ori_im, 0, 0 );                
                fprintf( 'DCT Compressive Image Recovery, Iter %d : PSNR = %f\n', iter, PSNR );
            end
        end
        
        for ii = 1 : 3
            fb        =   A( f(:) );
            f         =   f + lamada.*reshape(At( y-fb ), h, w);
        end        
        f          =   DCT_thresholding( f, par, D );
    end
    im     =  f;
end
Rec_im0   =  im;
return;


