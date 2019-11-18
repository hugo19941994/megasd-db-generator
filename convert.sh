for i in "libretro-imgs/*/Named_Titles/*.png"; do
	convert "$i" -resize 64x40\! +dither -colors 15 "output/$i"
done
