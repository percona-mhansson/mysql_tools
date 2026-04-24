asan=0
clang=1
build_home="build.dir"

build_type=${1:-Debug}
build_dir=${2:-${build_home}/${build_type,,}}

echo "build type ${build_type}"
echo "build dir ${build_dir}"

if [ "$clang" == "1" ]; then
   clang_opt="-DCMAKE_C_COMPILER=clang-18 -DCMAKE_CXX_COMPILER=clang++-18"
   build_dir="$build_dir.clang"
fi

if [ "$asan" == 1 ]; then
   asan_opt="-DWITH_ASAN=ON"
fi

cmd="cmake -B ${build_dir} -GNinja -DCMAKE_BUILD_TYPE=$build_type \
     -DDOWNLOAD_BOOST=1 -DWITH_BOOST=~/boost \
     -DWITH_AUTHENTICATION_LDAP=OFF -DWITH_PERCONA_AUTHENTICATION_LDAP=OFF \
     -DCMAKE_EXPORT_COMPILE_COMMANDS=ON -DFORCE_COLORED_OUTPUT=ON \
     -DWITH_LD=mold \
     $clang_opt \
     $asan_opt"

echo $cmd

cat > .clangd <<EOF
CompileFlags:
  CompilationDatabase: ${build_dir}
EOF

${cmd} #&& time ninja -C "$build_dir"
