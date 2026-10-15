-- MySQL Workbench Forward Engineering

SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0;
SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0;
SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='ONLY_FULL_GROUP_BY,STRICT_TRANS_TABLES,NO_ZERO_IN_DATE,NO_ZERO_DATE,ERROR_FOR_DIVISION_BY_ZERO,NO_ENGINE_SUBSTITUTION';

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------

-- -----------------------------------------------------
-- Schema mydb
-- -----------------------------------------------------
CREATE SCHEMA IF NOT EXISTS `mydb` DEFAULT CHARACTER SET utf8 ;
USE `mydb` ;

-- -----------------------------------------------------
-- Table `mydb`.`Usuario`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`Usuario` (
  `idUsuario` INT NOT NULL AUTO_INCREMENT,
  `nome` VARCHAR(255) NOT NULL,
  `senha` VARCHAR(255) NOT NULL,
  `email` VARCHAR(255) NOT NULL,
  PRIMARY KEY (`idUsuario`),
  UNIQUE INDEX `email_UNIQUE` (`email` ASC))
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `mydb`.`Texto`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`Texto` (
  `idTexto` INT NOT NULL AUTO_INCREMENT,
  `titulo` VARCHAR(255) NULL,
  `genero` VARCHAR(100) NULL,
  `tema` VARCHAR(255) NULL,
  `conteudo` TEXT NULL,
  `Usuario_idUsuario` INT NOT NULL,
  PRIMARY KEY (`idTexto`, `Usuario_idUsuario`),
  INDEX `fk_Texto_Usuario_idx` (`Usuario_idUsuario` ASC),
  CONSTRAINT `fk_Texto_Usuario`
    FOREIGN KEY (`Usuario_idUsuario`)
    REFERENCES `mydb`.`Usuario` (`idUsuario`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


-- -----------------------------------------------------
-- Table `mydb`.`correcoes`
-- -----------------------------------------------------
CREATE TABLE IF NOT EXISTS `mydb`.`correcoes` (
  `idcorrecoes` INT NOT NULL AUTO_INCREMENT,
  `nota` float NULL,
  `nEstrutura` float Null,
  `nTema` float Null,
  `nGramatica` float Null,
  `nRepertorio` float Null,
  `nCoesao` float Null,
  `quant_erros` INT NULL,
  `recomendacoes` TEXT NULL,
  `data_correcao` DATETIME NULL,
  `Texto_idTexto` INT NOT NULL,
  PRIMARY KEY (`idcorrecoes`, `Texto_idTexto`),
  INDEX `fk_correcoes_Texto1_idx` (`Texto_idTexto` ASC),
  CONSTRAINT `fk_correcoes_Texto1`
    FOREIGN KEY (`Texto_idTexto`)
    REFERENCES `mydb`.`Texto` (`idTexto`)
    ON DELETE NO ACTION
    ON UPDATE NO ACTION)
ENGINE = InnoDB;


SET SQL_MODE=@OLD_SQL_MODE;
SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS;
SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS;