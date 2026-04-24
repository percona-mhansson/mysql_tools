asan=1
build_type=${1:-Debug}

build_dir=build.dir/${build_type,,}

if [ "$asan" == 1 ]; then
  asan_opt="-DWITH_ASAN=ON"
  build_dir="$build_dir.asan"
fi

cmd="cmake -B ${build_dir} -GNinja -DCMAKE_BUILD_TYPE=$build_type \
     -DDOWNLOAD_BOOST=1 -DWITH_BOOST=~/boost \
     -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DFORCE_COLORED_OUTPUT=ON \
     $asan_opt"

echo $cmd

cat > .clangd <<EOF
CompileFlags:
  CompilationDatabase: ${build_dir}
EOF

${cmd} && time ninja -C "$build_dir"
