import sys, PIL.Image as I
fs=sys.argv[2:]; ims=[I.open(f).resize((960,540)) for f in fs]
cols=2; rows=(len(ims)+1)//2; M=I.new('RGB',(960*cols,540*rows))
for k,im in enumerate(ims): M.paste(im,((k%cols)*960,(k//cols)*540))
M.save(sys.argv[1],quality=85)
