# lively-luxtts

　　这是一个小说音频生成软件。它能分解txt小说的章节，根据不同的角色，生成不同音色的音频。生成音频的RTF速度（rtx 4070 laptop）是0.05-0.15间，生成3000字的章节，最快只需30秒。
![管理界面](https://github.com/normantest1/lively/blob/325c914f2b0886e672b94f76964871015d601389/asset/lively%E6%BC%94%E7%A4%BA.gif)

# 如何使用它
本项目可以再linux/windows下运行
> python >= 3.12
> 
> pytorch = 2.10
> 
> cuda = 12.8
1. 克隆项目
```shell
#克隆本项目
git clone https://github.com/normantest1/lively.git
#进入目录
cd lively
```
2. 运行pip安装命令

```shell
pip install -r requirements.txt
```
3. 下载模型

下载huggingface_hub
```shell
pip install huggingface_hub
```
如果你是国内环境，则需要设置huggingface_hub的镜像源
```shell
export HF_ENDPOINT=https://hf-mirror.com
```
下载luxtts模型
```shell
hf download YatharthS/LuxTTS --local-dir ./LuxTTS/
```

5. 运行

运行命令
```shell
python api.py
```
6. 访问
之后访问 http://127.0.0.1:6888
##### 访问后台管理系统后
1. 软件得使用支持Anthropic API的AI分析文本，所以在设置页面添加大模型的api_key、model_name和base_url
2. 上传小说
3. 在角色音频管理点击刷新
4. 在角色管理为旁白绑定角色音频
5. 使用定时任务解析小说文本
6. 使用定时任务根据解析文本生成音频

##### 自定义角色音频
1. 在audios下新添加角色名称的文件夹
2. 将wav音频命名成audio.wav
3. 将角色音频的性别写入到gender.txt文件内
4. 将角色音频的文本写入到text.txt文件内
5. 后台角色音频管理刷新角色