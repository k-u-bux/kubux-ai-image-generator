{
  description = "Kubux AI Image Generator";

  inputs = {
    nixpkgs.url = "github:NixOS/nixpkgs/nixos-25.05";
    flake-utils.url = "github:numtide/flake-utils";
  };

  outputs = { self, nixpkgs, flake-utils }:
    flake-utils.lib.eachDefaultSystem (system:
      let
        pkgs = nixpkgs.legacyPackages.${system};
        
        # Create the together package using fetchPypi
        togetherPkg = pkgs.python3Packages.buildPythonPackage rec {
          pname = "together";
          version = "1.5.21";
          format = "wheel";

          src = pkgs.fetchPypi {
            inherit pname version format;
            sha256 = "sha256-NebAByAzouXxEF3oeB6Wn0HP/IXa5Qi29NwpM2ACaHI=";
            dist = "py3";
            python = "py3";
          };

          # Dependencies based on together's requirements
          propagatedBuildInputs = with pkgs.python3Packages; [
            requests
            pydantic
            typing-extensions
            aiohttp
            httpx
            anyio
            distro
            sniffio
            filelock
            rich
            tqdm
          ];

          # Skip tests as they might require API keys
          doCheck = false;

          meta = with pkgs.lib; {
            description = "Python client for Together AI API";
            homepage = "https://pypi.org/project/together/";
            license = licenses.mit;
          };
        };
        
        # Define Python environment with all required packages including together
        pythonEnv = pkgs.python3.withPackages (ps: with ps; [
          tkinter
          pillow
          requests
          python-dotenv
          togetherPkg
        ]);
        
      in
      {
        packages.default = pkgs.stdenv.mkDerivation {
          pname = "kubux-ai-image-generator";
          version = "1.0.0";
          
          src = ./.;
          
          buildInputs = [ pythonEnv pkgs.imagemagick ];
          nativeBuildInputs = [ pkgs.makeWrapper ];
          
          installPhase = ''
            mkdir -p $out/bin
            mkdir -p $out/share/applications
            mkdir -p $out/share/icons/hicolor/{16x16,22x22,24x24,32x32,48x48,64x64,128x128,256x256}/apps

            # Copy the Python script
            cp kubux-ai-image-generator.py $out/bin/kubux-ai-image-generator.py
            cp probe_font.py $out/bin/probe_font.py
            chmod +x $out/bin/kubux-ai-image-generator.py
            
            # Create wrapper using makeWrapper for proper desktop integration
            makeWrapper ${pythonEnv}/bin/python $out/bin/kubux-ai-image-generator \
              --add-flags "$out/bin/kubux-ai-image-generator.py" \
              --set-default TMPDIR "/tmp"
            
            # Copy desktop file
            cp kubux-ai-image-generator.desktop $out/share/applications/

	    # create icons
	    bash create_icons.sh app-icon.png kubux-ai-image-generator
	    
            # Copy icons to all size directories
            for size in 16x16 22x22 24x24 32x32 48x48 64x64 128x128 256x256; do
              if [ -f hicolor/$size/apps/kubux-ai-image-generator.png ]; then
                cp hicolor/$size/apps/kubux-ai-image-generator.png $out/share/icons/hicolor/$size/apps/
              fi
            done
          '';
          
          meta = with pkgs.lib; {
            description = "AI-powered ai-image creation tool";
            homepage = "https://github.com/kubux/kubux-ai-image-generator";
            license = licenses.asl20;
            maintainers = [ ];
            platforms = platforms.linux;
          };
        };
        
        # Development shell with all dependencies for efficient testing
        devShells.default = pkgs.mkShell {
          buildInputs = with pkgs; [
	    python3
            pythonEnv
            imagemagick
            # Additional development tools
	    jetbrains.pycharm-community
	    python3Packages.scancode-toolkit
	    python3Packages.cython
            python3Packages.pip
            python3Packages.black
            python3Packages.flake8
          ];
          
          shellHook = ''
	    export SCANCODE_CACHE=$HOME/.cache/scancode-cache
	    export SCANCODE_LICENSE_INDEX_CACHE=$HOME/.cache/scancode-license-cache
	    ln -s $( which python ) python
            echo "Kubux Ai-Image Generator development environment"
            echo "Python with all dependencies available:"
            echo "  - tkinter, pillow, requests, python-dotenv"
            echo "  - together (from PyPI)"
            echo ""
            echo "You can now run: python kubux-ai-image-generator.py"
	    echo ""
	    echo "A symlink to the actual python interpreter is provided for PyCharm"
	    cleanup() {
	        echo "Cleaning up development environment..."
		if [ -L ./python ]; then
      		  rm ./python
    		fi
		if [ -L ./result ]; then
      		  rm ./result
    		fi
  	    }
  	    trap cleanup EXIT
          '';
        };
      });
}