from pathlib import Path
import os
import subprocess
import getpass
import pytest
import yaml

ROOT=Path(__file__).resolve().parents[1]
NAMES=['range42','range42-playbooks','range42-catalog','range42-backend-api','range42-deployer-ui',
       'range42-ansible_roles-proxmox_controller','range42-ansible_roles-debug-devkit']

@pytest.mark.parametrize('invalid',[False,True])
def test_release_pins_select_exact_commits_and_reject_unknown_repositories_before_cloning(tmp_path,invalid):
    source=tmp_path/'source';subprocess.run(['git','init','-q','-b','main',str(source)],check=True)
    (source/'public').write_text('first')
    def commit(message):
        subprocess.run(['git','-C',str(source),'add','.'],check=True)
        subprocess.run(['git','-C',str(source),'-c','user.name=Fixture','-c','user.email=fixture@example.invalid','commit','-qm',message],check=True)
        return subprocess.check_output(['git','-C',str(source),'rev-parse','HEAD'],text=True).strip()
    first=commit('first');(source/'public').write_text('new main');commit('second')
    gitconfig=tmp_path/'gitconfig'
    for name in NAMES:
        subprocess.run(['git','config','--file',str(gitconfig),'--add','url.'+source.as_uri()+'.insteadOf','https://github.com/range42/'+name+'.git'],check=True)
    pins={name:first for name in NAMES}
    if invalid:pins['unknown-repository']=first
    release=tmp_path/'release.yml';release.write_text(yaml.safe_dump(pins))
    destination=tmp_path/'installed'
    play=tmp_path/'play.yml';play.write_text(yaml.safe_dump([{'hosts':'localhost','gather_facts':False,'vars':{
        'ansible_connection':'local','ansible_become':False,'ansible_python_interpreter':os.sys.executable,
        'DEPLOYER_CLI_USER':getpass.getuser(),'DEPLOYER_CLI__DST_GIT_DIR':str(destination)},'roles':['deployer.repos']}]))
    env={k:v for k,v in os.environ.items() if not k.startswith('ANSIBLE_')}
    env.update(ANSIBLE_ROLES_PATH=str(ROOT/'roles'),GIT_CONFIG_GLOBAL=str(gitconfig),RANGE42_REPOSITORY_REVISIONS_FILE=str(release))
    result=subprocess.run(['ansible-playbook','-i','localhost,',str(play)],env=env,capture_output=True,text=True,timeout=60)
    if invalid:
        assert result.returncode!=0
        assert not list(destination.glob('*/.git'))
    else:
        assert result.returncode==0,result.stdout+result.stderr
        for name in NAMES:
            actual=subprocess.check_output(['git','-C',str(destination/name),'rev-parse','HEAD'],text=True).strip()
            assert actual==first,'Installer silently replaced the selected release with main'
