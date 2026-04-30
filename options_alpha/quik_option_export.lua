-- quik_option_export.lua
-- Скрипт для экспорта опционной доски в TSV формат

local timer = 0
local INTERVAL = 5 -- Интервал обновления в секундах

-- Путь куда сохранять файл
local OUTPUT_DIR = "C:\\Project\\Option Analitik\\data"
local FILE_TMP = OUTPUT_DIR .. "\\option_export.tmp"
local FILE_OUT = OUTPUT_DIR .. "\\option_export.tsv"

local ASSET_CODE = "SiM6" -- Фьючерс (базовый актив), измените на актуальный код! (Например SiM4, SiZ4)

function main()
    message("Экспорт опционов запущен. Папка: " .. OUTPUT_DIR)
    while true do
        timer = timer + 1
        if timer >= INTERVAL then
            timer = 0
            export_data()
        end
        sleep(1000)
    end
end

function export_data()
    -- Получение цены базового актива
    local underlying_price = getParamEx("SPBFUT", ASSET_CODE, "last").param_value
    if underlying_price == "0.000000" or underlying_price == "" then
        underlying_price = getParamEx("SPBFUT", ASSET_CODE, "settleprice").param_value
    end

    -- Записываем во временный файл
    local file = io.open(FILE_TMP, "w")
    if not file then
        message("Ошибка создания временного файла: " .. FILE_TMP)
        return
    end

    file:write("sec_code\tstrike\tbid\task\tlast\ttype\texpiry_date\tunderlying_asset\tunderlying_price\tiv\topen_interest\n")

    local classes = "SPBOPT"
    local num_papers = getNumberOf("securities")

    for i = 0, num_papers - 1 do
        local sec = getItem("securities", i)
        if sec and sec.class_code == classes and string.find(sec.code, "Si") then
            local sec_code = sec.code
            local strike = getParamEx(classes, sec_code, "strike").param_value
            local bid = getParamEx(classes, sec_code, "bid").param_value
            local ask = getParamEx(classes, sec_code, "offer").param_value
            local last = getParamEx(classes, sec_code, "last").param_value
            local iv = getParamEx(classes, sec_code, "volatility").param_value
            local oi = getParamEx(classes, sec_code, "numpcontracts").param_value
            
            local opt_type = "call"
            if string.find(sec.name, "Путы") or string.find(sec.name, "Put") then
                opt_type = "put"
            end
            
            local expiry_date = sec.mat_date -- формат YYYYMMDD

            file:write(sec_code .. "\t" .. strike .. "\t" .. bid .. "\t" .. ask .. "\t" .. last .. "\t" .. opt_type .. "\t" .. expiry_date .. "\t" .. ASSET_CODE .. "\t" .. underlying_price .. "\t" .. iv .. "\t" .. oi .. "\n")
        end
    end

    file:close()
    
    -- Переименовываем tmp в tsv. Это мгновенная операция ОС.
    -- Python не поймает файл на моменте его пустой очистки!
    os.remove(FILE_OUT)
    os.rename(FILE_TMP, FILE_OUT)
end

function OnStop()
    message("Экспорт опционов остановлен.")
    return 1000
end