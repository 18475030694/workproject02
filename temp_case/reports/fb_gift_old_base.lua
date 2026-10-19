---@diagnostic disable: unnecessary-if, undefined-field
local Class = require "glib.class"
local Res = require 'glib.share_res'
local Date = require "glib.extend.date"
local Table = require 'glib.extend.table'
local LobbyDefine = import 'service.lobby.defines'

local ResHelper = import "modules.utils.res_helper"
local RechargeUtils = import "service.lobby.recharge.utils"
local RechargeDefines = import "service.lobby.recharge.defines"
local ConditionHelper = import "service.lobby.condition.condition_helper"

local pairs = pairs
local ONE_HOUR = 3600

local FbTimerName = "FbTimer"
local GiftCfgPath = "recharge.cfg_fb_gift"
local RECHARGE_PROJECT_SYS = RechargeDefines.RECHARGE_PROJECT_SYS

---@description 上架物品结构
---@class clsSellData
---@field goods_id number       -- 商品ID
---@field end_time number       -- 上架结束时间
---@field start_time number     -- 上架开始时间
local clsSellData = {
    goods_id = 0,
    end_time = -1,
    start_time = -1
}

---@description 购买信息
---@class clsFbBuyData
---@field goods_id number
---@field count number
---@field recv_record_list fb_gift_recv_record
local clsFbBuyData = {
    goods_id = 0,
    count = 0,
    recv_record_list = {}
}

-------------------------------------------------------------------法宝礼包-------------------------------------------------------------------
---@description 孙悟空法宝礼包
---@class CFbGiftPack
---@field player any 玩家对象
---@field module any 充值模块
---@field buyList table<number,clsFbBuyData> 购买列表
---@field goodsList table<number,clsSellData> 上架礼包列表
---@field conditionHelper any 条件管理器
CFbGiftPack = Class("CFbGiftPack")

---@description 初始化
---@param player any 玩家对象
---@param module any 充值模块
---@return CFbGiftPack
function CFbGiftPack:init(player, module)
    self.player = player
    self.module = module
    self.buyList = {}
    self.goodsList = {}
    self.conditionHelper = ConditionHelper.CConditionHelper:New(self, self.player)
    return self
end

---@description 加载数据
---@param data table?
---@return boolean
function CFbGiftPack:Load(data)
    if data then
        self.buyList = data.buy_list or self.buyList
        self.goodsList = data.goods_list or self.goodsList
        self.conditionHelper:Load(data.condition or {})

        -- 数据兼容
        for k, v in pairs(self.buyList) do
            if not v.recv_record_list then
                v.day_no = 1
                v.recv_record_list = {{
                    day = 1,
                    status = true
                }}
            end
        end
    end

    return true
end

---@description 保存数据
---@return table
function CFbGiftPack:Save()
    return {
        buy_list = self.buyList,
        goods_list = self.goodsList,
        condition = self.conditionHelper:GetSaveData()
    }
end

---@description 释放对象
---@return boolean
function CFbGiftPack:Release()
    self.conditionHelper:Release()
    self:StopCheckTimer()
    return true
end

---@description 停止定时器
---@return boolean
function CFbGiftPack:StopCheckTimer()
    self.player:RemoveCallOut(FbTimerName)
    return true
end

---@description 启动定时器
---@return boolean
function CFbGiftPack:StartCheckTimer()
    self:StopCheckTimer()
    self:CheckGoodsTimeout(true)
    local uuid = self.player:GetUUID()
    if Table.Empty(self.goodsList) then
        Log.Infof("[CFbGiftPack] there is no fb_gift sell, player: %d", uuid)
        return false
    end

    ---@type clsSellData[]
    local goodsList = Table.TransValueToList(self.goodsList)
    table.sort(goodsList, function(goodsA, goodsB)
        return goodsA.end_time < goodsB.end_time
    end)

    local goodsInfo = goodsList[1]
    local goodsId = goodsInfo and goodsInfo.goods_id or -1
    local second = goodsInfo and (goodsInfo.end_time - Date.Second()) or -1
    if 0 < second and 0 < goodsId then
        self.player:CallOut(FbTimerName, function()
            self:StartCheckTimer()
        end, second)
        Log.Infof("[CFbGiftPack] start timer, player: %d, id: %d, second: %d", uuid, goodsId, second)
    end

    return true
end

---@description 上架新礼包
---@param giftCfg table
---@return clsSellData
function CFbGiftPack:GenNewSaleGoods(giftCfg)
    local goodsId = giftCfg.id
    local limitTime = giftCfg.limit_time
    local newGoods = {
        goods_id = goodsId,
        end_time = limitTime and (Date.Second() + limitTime * ONE_HOUR) or -1,
        start_time = Date.Second()
    }
    self.goodsList[goodsId] = newGoods
    self.module:SetDirty()
    self.player:SyncToClient("gs2c_recharge_fb_gift_new", {
        new_goods = newGoods
    })
    self:StartCheckTimer()
    Log.Infof("[CFbGiftPack] start sell new goods, player: %d, goods_id: %d", self.player:GetUUID(), goodsId)
    return newGoods
end

---@description 删除已上架礼包
---@param goodsId number 礼包ID
---@param notify boolean 是否通知客户端
---@return boolean
function CFbGiftPack:DeleteGoodsById(goodsId, notify)
    local buyData = self.buyList[goodsId] or {
        goods_id = goodsId,
        count = 0,
        day_no = 1,
        recv_record_list = {{
            day = 1,
            status = false
        }}
    }
    self.buyList[goodsId] = buyData
    self.goodsList[goodsId] = nil
    if notify then
        self.player:SyncToClient("gs2c_recharge_fb_gift_down", {
            goods_id = goodsId
        })
    end

    self.module:SetDirty()
    return true
end

---@description 校验礼包过期
---@param notify boolean 是否通知客户端
---@return boolean
function CFbGiftPack:CheckGoodsTimeout(notify)
    local now = Date.Second()
    local giftCfgList = Res.GetResources(GiftCfgPath)

    for goodsId, goodsData in pairs(self.goodsList) do
        local giftCfg = giftCfgList[goodsId]
        if not giftCfg then
            -- 礼包配置不存在了
            self:DeleteGoodsById(goodsId, notify)
            Log.Infof("[CFbGiftPack] cfg not exist, player: %d, goods_id: %d, end_time: %d", self.player:GetUUID(), goodsId, goodsData.end_time or -1)
        else
            local limitTime = giftCfg.limit_time
            local sTime = goodsData.start_time or Date.Second()
            local eTime = limitTime and (sTime + limitTime * ONE_HOUR) or -1
            goodsData.end_time = eTime
            goodsData.start_time = sTime
            if 0 < eTime and eTime <= now then
                -- 礼包过期下架
                self:DeleteGoodsById(goodsId, notify)
                Log.Infof("[CFbGiftPack] overtime, player: %d, goods_id: %d, end_time: %d", self.player:GetUUID(), goodsId, goodsData.end_time or -1)
            end
        end
    end

    return true
end

---@description 注册礼包上架事件
---@return boolean
function CFbGiftPack:RegGoodsEvent()
    local giftCfgList = Res.GetResources(GiftCfgPath)
    local callbackData = {
        reachFunc = "OnGoodsStartSale"
    }

    for _, giftCfg in pairs(giftCfgList) do
        local goodsId = giftCfg.id
        if (not self.buyList[goodsId]) and (not self.goodsList[goodsId]) then
            local extraParam = {
                infoKey = goodsId,
                goodsId = goodsId
            }
            if giftCfg.condition and (not Table.Empty(giftCfg.condition)) then
                -- 注册礼包上架条件
                self.conditionHelper:AddConditionInfoFromCfg(giftCfg, callbackData, extraParam, true)
            else
                self:GenNewSaleGoods(giftCfg)
            end
        end
    end

    return true
end

---@description 礼包上架回调
---@param condInfo table
---@return boolean
function CFbGiftPack:OnGoodsStartSale(condInfo)
    local uuid = self.player:GetUUID()
    local goodsId = condInfo:IsReach() and condInfo:GetExtraVal("goodsId")
    if (not goodsId) or self.buyList[goodsId] or self.goodsList[goodsId] then
        Log.Infof("[CFbGiftPack] cannot start sale, player: %d, goods_id: %d", uuid, goodsId or -1)
        return false
    end

    local giftCfgList = Res.GetResources(GiftCfgPath)
    local giftCfg = giftCfgList and giftCfgList[goodsId]
    if not giftCfg then
        Log.Infof("[CFbGiftPack] sale gift cfg not exist, player: %d, goods_id: %d", uuid, goodsId or -1)
        return false
    end

    self:GenNewSaleGoods(giftCfg)
    return true
end

---@description 上线回调接口
---@return boolean
function CFbGiftPack:SceneReady()
    self:CheckGoodsTimeout(false)
    local goodsList = Table.TransValueToList(self.goodsList)

    for goodsId, v in pairs(self.buyList) do

        if not self:IsGetAllReward(goodsId) then
            local item = {
                goods_id = goodsId,
                end_time = -1,
                recv_record_list = v.recv_record_list
            }

            table.insert(goodsList, item)
        end
    end

    self.player:SyncToClient("gs2c_recharge_fb_gift_info", {
        goods_list = goodsList
    })
    self:RegGoodsEvent()
    self:StartCheckTimer()
    return true
end

---@description 系统开启回调
---@return boolean
function CFbGiftPack:SyncGiftInfo(goodsId)
    local info = self.goodsList[goodsId]

    if not info and self.buyList[goodsId] and not self:IsGetAllReward(goodsId) then
        info = {
            goods_id = goodsId,
            end_time = -1,
            recv_record_list = self.buyList[goodsId].recv_record_list
        }
    end
    self.player:SyncToClient("gs2c_recharge_fb_gift_update", {
        goods_info = info
    })
end

---@description 系统开启回调
---@return boolean
function CFbGiftPack:OpenSysAction()
    self:SceneReady()
    return true
end

---@description 天刷新
function CFbGiftPack:OnDailyReset()
    local giftCfgList = Res.GetResources(GiftCfgPath)

    local todayNo = Date.TodayNo()

    for goodsId, buyData in pairs(self.buyList) do
        local giftCfg = giftCfgList[goodsId]

        local recvRecordList = buyData.recv_record_list

        for dayNo = #recvRecordList + 1, todayNo - buyData.day_no + 1 do
            local field = "reward_list" .. dayNo
            if not giftCfg[field] then
                break
            end

            recvRecordList[dayNo] = {
                day = dayNo,
                status = false
            }
        end
    end
end

---@description 校验购买条件
---@param goodsCfg table
---@return number errCode
function CFbGiftPack:CheckBuyCondition(goodsCfg)
    local goodsId = goodsCfg.id
    local sellData = self.goodsList[goodsId]
    if not sellData then
        return CS_ERR_CODE_S2I.GOODS_SELL_OUT
    end

    -- 礼包是否过期已下架
    local eTime = sellData.end_time
    if (0 < eTime) and (eTime < Date.Second()) then
        return CS_ERR_CODE_S2I.RECHARGE_PUSH_GIFT_OVER_TIME
    end

    return ERRCODE_OK
end

---@description 构建购买后数据
---@param goodsCfg table
---@return number errCode
function CFbGiftPack:CreateBuyData(goodsCfg)
    local goodsId = goodsCfg.id
    local giftCfgList = Res.GetResources(GiftCfgPath)
    local giftCfg = giftCfgList and giftCfgList[goodsId]

    if not giftCfg then
        Log.Infof("[CFbGiftPack] giftCfg is nil, player: %d, goods_id: %d", self.player:GetUUID(), goodsId)
        return CS_ERR_CODE_S2I.CONFIG_ERROR
    end

    local buyData = self.buyList[goodsId] or {
        goods_id = goodsId,
        count = 0,
        day_no = 0,
        recv_record_list = {}
    }
    buyData.count = buyData.count + 1
    buyData.day_no = 1
    buyData.recv_record_list = {{
        day = 1,
        status = false
    }}

    self.buyList[goodsId] = buyData
    -- local addRewards = ResHelper.Item.CfgAwardListToRewardList(rewardList)
    -- self.player:RewardList(addRewards, "buy_fb_gift", {boAutoSyncItemRecord = true})
    self:DeleteGoodsById(goodsId, false)
    -- 系统消息
    self.player:GetModule(LobbyDefine.PLAYER_MODULE.CHAT):SendSystemCfgMsg(false, "FbPack", self.player:GetName())
    -- 跑马灯
    local bulletinCfg = Res.GetResources("bulletin.cfg_bulletin_msg")
    local fbFormat = bulletinCfg.FbPack
    if fbFormat then
        local content = string.format(fbFormat, self.player:GetName())
        self.player:SendBulletin(content)
    end

    return ERRCODE_OK
end

---@description 充值购买回调
---@param notifyKey string 商品KEY
---@return number errCode
function CFbGiftPack:RechargeAction(notifyKey)
    local goodsCfg = RechargeUtils.GetCfgByNotifyKey(notifyKey)
    local goodsId = goodsCfg and goodsCfg.id
    if not goodsId then
        local errMsg = {
            action = "recharge_err",
            notify_key = notifyKey
        }
        self.player:ReportErrf(errMsg, "fb_recharge_err, goods not exist, notify_key: %s", notifyKey)
        return CS_ERR_CODE_S2I.NOT_FIND_SDKKEY_ITEM
    end

    local errCode = self:CreateBuyData(goodsCfg)
    if errCode ~= ERRCODE_OK then
        local errMsg = {
            action = "recharge_err",
            notify_key = notifyKey
        }
        self.player:ReportErrf(errMsg, "fb_recharge_err CreateBuyData failed, id: %d, errcode: %d", goodsId, errCode)
        return errCode
    end

    self.module:SetDirty()
    self.player:DispatchEvent(LobbyDefine.LOBBY_EVENT.RECHARGE_SUCCESS, RECHARGE_PROJECT_SYS.FB_GIFT, goodsId)

    self:SyncGiftInfo(goodsId)

    return ERRCODE_OK
end

---@description 礼包购买校验
---@param notifyKey string 商品KEY
---@param goodsCfg table
---@return number errCode
function CFbGiftPack:CheckBuyGoodsBySDK(notifyKey, goodsCfg)
    local goodsId = goodsCfg.id
    local errCode = self:CheckBuyCondition(goodsCfg)
    if errCode ~= ERRCODE_OK then
        local errMsg = {
            action = "recharge_err",
            notify_key = notifyKey
        }
        self.player:ReportWarnf(errMsg, "fb_recharge_err, id: %d, errcode: %d", goodsId, errCode)
        return errCode
    end

    self.player:DispatchEvent(LobbyDefine.LOBBY_EVENT.TRY_RECHARGE, RECHARGE_PROJECT_SYS.FB_GIFT, goodsId)
    return ERRCODE_OK
end

---@description 是否领取所有奖励
---@param goodsId number 礼包ID
---@return boolean
function CFbGiftPack:IsGetAllReward(goodsId)
    local giftCfgList = Res.GetResources(GiftCfgPath)
    local giftCfg = giftCfgList and giftCfgList[goodsId]
    if not giftCfg then
        -- 配置都没有， 就当全领取了
        return true
    end

    local buyData = self.buyList[goodsId]
    if not buyData then
        -- 没有购买
        return false
    end

    local recvRecordList = buyData.recv_record_list or {}

    for i = 1, 10, 1 do
        local cfgReward = giftCfg["reward_list" .. i]
        if not cfgReward then
            break
        end

        local recvRecordItem = recvRecordList[i]
        if not recvRecordItem or not recvRecordItem.status then
            return false
        end
    end

    return true
end

---@description 领取礼包奖励
---@param goodsId number 礼包ID
---@return number errCode
function CFbGiftPack:C2gsGetFbGiftReward(goodsId)
    if not goodsId then
        return CS_ERR_CODE_S2I.PARAM_ERROR
    end

    local buyData = self.buyList[goodsId]
    if not buyData then
        return CS_ERR_CODE_S2I.NOT_BUY
    end

    local giftCfgList = Res.GetResources(GiftCfgPath)
    local giftCfg = giftCfgList and giftCfgList[goodsId]
    if not giftCfg then
        return CS_ERR_CODE_S2I.CONFIG_ERROR
    end

    local rewardList = {}
    for _, v in pairs(buyData.recv_record_list or {}) do
        if not v.status then
            local dayNo = v.day
            local cfgReward = giftCfg["reward_list" .. dayNo]
            if not cfgReward then
                break
            end

            ResHelper.Item.CfgAwardListToRewardList(cfgReward, rewardList)

            v.status = true
        end
    end

    if Table.Empty(rewardList) then
        return CS_ERR_CODE_S2I.REWARDS_RECEIVED
    end

    self.player:RewardList(rewardList, "buy_fb_gift", {
        boAutoSyncItemRecord = true
    })

    self:SyncGiftInfo(goodsId)

    if self:IsGetAllReward(goodsId) then
        self.player:SyncToClient("gs2c_recharge_fb_gift_down", {
            goods_id = goodsId
        })
    end

    return ERRCODE_OK
end
