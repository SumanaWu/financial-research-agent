import { Link } from 'react-router';
export default function LocalHelp() {
  return <main style={{maxWidth: 850, margin: '0 auto', padding: '48px 24px', lineHeight: 1.9}}>
    <Link to="/">返回工作台</Link>
    <h1>金融研究工作台使用说明</h1>
    <p>完整安装步骤、环境变量和模块阅读顺序，请查看源码包根目录 README.md。系统架构、Agent 编排、Memory 与恢复机制见随包的项目深度介绍文档。</p>
    <h2>开始研究</h2><p>在本地设置模型访问，创建计算机和工作区，再新建会话。数据工具需要在插件配置中启用；FMP 等服务需要相应凭证，免费行情也有可用性与配额限制。</p>
    <h2>执行环境与文件</h2><p>Docker、Daytona、E2B 或 SSH 负责运行研究代码。报告、数据和脚本保存在工作区中。工作区的代码可以访问同一计算机上该用户拥有的其他文件，敏感任务请使用单独的计算机环境。</p>
    <h2>模型与授权</h2><p>模型访问使用个人配置或部署者提供的凭证。支持的运行模式取决于已连接的计算机、可用模型和安装组件。缺少连接时先完成设置，再运行研究任务。</p>
    <h2>CLI 与持续任务</h2><p>CLI 的子命令与参数见 cli/README.md。自动化、工作流和通知需要后端服务持续运行。关闭页面与取消任务是不同的操作。</p>
    <h2>许可</h2><p>许可证与第三方声明保存在源码包中。</p><Link to="/legal">查看许可说明</Link>
  </main>;
}
